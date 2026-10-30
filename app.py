from functools import wraps
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import secrets
from leads_export import bp as leads_export_bp
from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    abort,
    g,
    send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import update, case
from models import db, Usuario, Categoria, Produto, Pedido, Item, Caixa, Movimento
from config import Config
from notifications import bp as notifications_bp, emit_order
from models import Notificacao, PushSubscription
from customers import bp as customers_bp
from orders_service import serialize_order, add_items
from customer_security import throttle
from couriers import bp as couriers_bp
from models import Entrega


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    from appearance import bp as appearance_bp

    app.register_blueprint(appearance_bp)
    app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
    db.init_app(app)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(leads_export_bp)
    app.register_blueprint(couriers_bp)

    @app.template_filter("data_br")
    def data_br(value):
        if not value:
            return ""
        return (
            value.replace(tzinfo=timezone.utc)
            .astimezone(ZoneInfo("America/Sao_Paulo"))
            .strftime("%d/%m/%Y %H:%M")
        )

    @app.template_filter("brl")
    def brl(v):
        return "R$ " + f"{v/100:,.2f}".replace(",", "X").replace(".", ",").replace(
            "X", "."
        )

    @app.before_request
    def load():
        g.user = (
            db.session.get(Usuario, session.get("uid")) if session.get("uid") else None
        )
        if g.user and not g.user.ativo:
            session.clear()
            g.user = None
        session.setdefault("csrf", secrets.token_hex(32))
        if request.method == "POST" and not secrets.compare_digest(
            str(session["csrf"]),
            str(request.headers.get("X-CSRF-Token") or request.form.get("csrf", "")),
        ):
            abort(400, "Sessão expirada. Atualize a página.")

    @app.context_processor
    def context():
        cursor = (
            db.session.scalar(
                db.select(db.func.max(Notificacao.id)).where(
                    Notificacao.usuario_id == g.user.id
                )
            )
            if g.user
            else 0
        )
        return dict(user=g.user, csrf=session["csrf"], event_cursor=cursor or 0)

    @app.after_request
    def security_headers(response):
        if request.endpoint != "static":
            response.headers.setdefault("Cache-Control", "no-store")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.get("/sw.js")
    def service_worker():
        response = send_from_directory(
            app.static_folder, "sw.js", mimetype="application/javascript"
        )
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/manifest.webmanifest")
    def manifest():
        return send_from_directory(
            app.static_folder,
            "manifest.webmanifest",
            mimetype="application/manifest+json",
        )

    def access(*roles):
        def deco(fn):
            @wraps(fn)
            def wrap(*a, **kw):
                if not g.user:
                    return (
                        redirect(url_for("login"))
                        if not request.path.startswith("/api")
                        else (jsonify(error="Faça login novamente."), 401)
                    )
                if roles and g.user.perfil not in roles:
                    abort(403)
                return fn(*a, **kw)

            return wrap

        return deco

    def money(v):
        try:
            n = Decimal(str(v).replace(",", "."))
            if (
                not n.is_finite()
                or n < 0
                or n > Decimal("1000000")
                or n.as_tuple().exponent < -2
            ):
                raise ValueError()
            return int(n * 100)
        except (InvalidOperation, ValueError):
            abort(400, "Informe um valor válido com até duas casas decimais.")

    def text(k, limit=100):
        s = str(request.form.get(k, "")).strip()
        if not s or len(s) > limit:
            abort(400, "Campo inválido: " + k)
        return s

    def current_cash():
        return db.session.scalar(db.select(Caixa).where(Caixa.fechado.is_(None)))

    def own(p):
        if g.user.perfil == "garcom" and p.online:
            abort(403)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(429)
    def error(e):
        db.session.rollback()
        if request.path.startswith("/api"):
            return jsonify(error=e.description), e.code
        return render_template("error.html", message=e.description), e.code

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            throttle("login", 50, 900)
            throttle("login-user:" + request.form.get("login", "")[:80], 10, 900)
            u = db.session.scalar(
                db.select(Usuario).where(
                    Usuario.login == request.form.get("login"), Usuario.ativo.is_(True)
                )
            )
            if u and check_password_hash(u.senha, request.form.get("senha", "")):
                previous_endpoint = (
                    session.get("push_endpoint")
                    if g.user and g.user.id == u.id
                    else None
                )
                if g.user and g.user.id != u.id and session.get("push_endpoint"):
                    db.session.execute(
                        update(PushSubscription)
                        .where(
                            PushSubscription.usuario_id == g.user.id,
                            PushSubscription.endpoint == session["push_endpoint"],
                        )
                        .values(ativo=False)
                    )
                    db.session.commit()
                session.clear()
                session["uid"] = u.id
                if previous_endpoint:
                    session["push_endpoint"] = previous_endpoint
                return redirect(
                    url_for("customers.menu")
                    if u.perfil == "cliente"
                    else url_for("home")
                )
            error = "Usuário ou senha incorretos."
        return render_template("login.html", error=error)

    @app.post("/logout")
    def logout():
        if g.user and session.get("push_endpoint"):
            db.session.execute(
                update(PushSubscription)
                .where(
                    PushSubscription.usuario_id == g.user.id,
                    PushSubscription.endpoint == session["push_endpoint"],
                )
                .values(ativo=False)
            )
            db.session.commit()
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    def home():
        if g.user and g.user.perfil == "admin":
            return redirect(url_for("pedidos"))
        if not g.user or g.user.perfil == "cliente":
            return redirect(url_for("customers.menu"))
        if g.user.perfil == "entregador":
            return redirect(url_for("couriers.deliveries"))
        return redirect(
            url_for("pedidos") if g.user.perfil == "cozinha" else url_for("pdv")
        )

    @app.get("/pdv")
    @access("admin", "garcom")
    def pdv():
        return render_template(
            "pdv.html",
            categorias=db.session.scalars(db.select(Categoria)).all(),
            produtos=db.session.scalars(
                db.select(Produto).where(Produto.ativo.is_(True))
            ).all(),
        )

    @app.route("/pedidos")
    @access("admin", "garcom", "cozinha")
    def pedidos():
        return render_template("pedidos.html")

    @app.get("/api/pedidos")
    @access("admin", "garcom", "cozinha")
    def list_orders():
        q = db.select(Pedido)
        if g.user.perfil == "admin":
            priority = case(
                (Pedido.status == "entregue", 0),
                (Pedido.status == "pronto", 1),
                (Pedido.status == "em_preparo", 2),
                (Pedido.status == "aberto", 3),
                (Pedido.status == "saiu_entrega", 4),
                else_=5,
            )

            # Tele-entregas prontas aguardando encaminhamento ficam no topo.
            tele_entrega_pronta = (
                (Pedido.status == "pronto")
                & Pedido.online.has(modalidade="entrega")
            )

            q = q.order_by(
                case(
                    (tele_entrega_pronta, 0),
                    else_=1,
                ),
                Pedido.pago.asc(),
                priority,
                Pedido.id.desc(),
            )
        elif g.user.perfil == "garcom":
            priority = case(
                (Pedido.status == "pronto", 0),
                (Pedido.status == "em_preparo", 1),
                (Pedido.status == "aberto", 2),
                else_=3,
            )

            q = (
                db.select(Pedido)
                .where(
                    # Somente pedidos registrados no PDV do salão.
                    Pedido.online.has(),

                    # Entregues ficam fora da lista do garçom.
                    Pedido.status.in_(["aberto", "em_preparo", "pronto"]),
                )
                .order_by(
                    priority,
                    Pedido.id.desc(),
                )
            )
        elif g.user.perfil == "cozinha":
            # Pedidos prontos deixam a fila da cozinha.
            priority = case(
                (Pedido.status == "aberto", 0),
                (Pedido.status == "em_preparo", 1),
                else_=2,
            )
            q = q.where(Pedido.status.in_(["aberto", "em_preparo"])).order_by(
                priority, Pedido.id.desc()
            )
        q = q.limit(200)
        return jsonify([serialize_order(p, g.user) for p in db.session.scalars(q)])

    @app.get("/api/pedidos/<int:id>/detalhes")
    @access("admin", "garcom", "cozinha", "cliente")
    def order_details(id):
        p = db.get_or_404(Pedido, id)
        own(p)
        if g.user.perfil == "cliente" and (not p.online or p.usuario_id != g.user.id):
            abort(403)
        return jsonify(serialize_order(p, g.user))

    @app.post("/api/pedidos")
    @access("admin", "garcom")
    def new_order():
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            abort(400, "Pedido inválido.")
        mesa = d.get("mesa", "")
        if not isinstance(mesa, str) or not mesa.strip() or len(mesa) > 40:
            abort(400, "Informe a mesa.")
        p = Pedido(mesa=mesa.strip(), usuario_id=g.user.id)
        add_items(p, d.get("itens"))
        db.session.add(p)
        db.session.flush()
        emit_order(p, "novo")
        db.session.commit()
        return jsonify(id=p.id), 201

    @app.post("/api/pedidos/<int:id>/status")
    @access("admin", "garcom", "cozinha")
    def status(id):
        p = db.get_or_404(Pedido, id)
        own(p)
        target = (request.get_json(silent=True) or {}).get("status")
        if (
            target == "entregue"
            and p.online
            and p.online.modalidade == "entrega"
        ):
            abort(
                409,
                "A tele-entrega deve ser confirmada pelo entregador."
            )
        allowed = {
            "aberto": "em_preparo",
            "em_preparo": "pronto",
            "pronto": (
                "saiu_entrega"
                if p.online and p.online.modalidade == "entrega"
                else "entregue"
            ),
            "saiu_entrega": "entregue",
        }
        if allowed.get(p.status) != target:
            abort(409, "O pedido mudou. Atualize a tela.")
        if (
            g.user.perfil == "garcom"
            and (target != "entregue" or p.online)
            or g.user.perfil == "cozinha"
            and target not in ["em_preparo", "pronto"]
        ):
            abort(403)
        result = db.session.execute(
            update(Pedido)
            .where(Pedido.id == id, Pedido.status == p.status)
            .values(status=target)
        )
        if result.rowcount != 1:
            abort(409, "Pedido atualizado por outra pessoa.")
        emit_order(p, target)
        db.session.commit()
        return jsonify(ok=True)

    @app.post("/api/pedidos/<int:id>/pagar")
    @access("admin")
    def pay(id):
        db.session.rollback()
        db.session.execute(db.text("BEGIN IMMEDIATE"))
        p = db.get_or_404(Pedido, id)
        caixa = current_cash()
        forma = (request.get_json(silent=True) or {}).get("forma")
        if not caixa:
            abort(409, "Abra o caixa antes de receber.")
        if forma not in ["dinheiro", "pix", "credito", "debito"]:
            abort(400, "Forma inválida.")
        if p.pago:
            abort(409, "Pedido já pago.")
        if p.entrega and p.entrega.entregue_em and not p.entrega.acertado_em:
            abort(409, "Confira este recebimento em Acerto de entregadores.")
        result = db.session.execute(
            update(Pedido)
            .where(Pedido.id == id, Pedido.pago.is_(False))
            .values(pago=True)
        )
        if result.rowcount != 1:
            abort(409, "Pagamento já registrado.")
        db.session.add(
            Movimento(
                caixa_id=caixa.id,
                pedido_id=id,
                tipo="recebimento",
                forma=forma,
                valor=p.total,
                descricao=f"Pedido #{id}",
            )
        )
        emit_order(p, "pago")
        db.session.commit()
        return jsonify(ok=True)

    @app.route("/cadastros/<kind>", methods=["GET", "POST"])
    @access("admin")
    def cadastros(kind):
        classes = {"produtos": Produto, "categorias": Categoria, "usuarios": Usuario}
        if kind not in classes:
            abort(404)
        cls = classes[kind]
        if request.method == "POST":
            id = request.form.get("id")
            obj = db.get_or_404(cls, int(id)) if id and id.isdigit() else cls()
            if kind == "usuarios" and obj.id and obj.perfil == "cliente":
                abort(403)
            obj.nome = text("nome", 80)
            if kind == "produtos":
                obj.preco = money(request.form.get("preco"))
                obj.descricao = request.form.get("descricao", "")[:500]
                obj.emoji = request.form.get("emoji", "🍽️")[:10]
                cat = request.form.get("categoria_id", "")
                if not cat.isdigit() or not db.session.get(Categoria, int(cat)):
                    abort(400, "Categoria inválida.")
                obj.categoria_id = int(cat)
                obj.ativo = request.form.get("ativo") == "on"
            if kind == "usuarios":
                obj.login = text("login", 80)
                perfil = request.form.get("perfil")
                if perfil not in ["admin", "garcom", "cozinha", "entregador"]:
                    abort(400, "Perfil inválido.")
                if obj.id == g.user.id and (
                    perfil != "admin" or request.form.get("ativo") != "on"
                ):
                    abort(400, "Você não pode desativar ou rebaixar sua própria conta.")
                if (
                    obj.id
                    and obj.perfil == "entregador"
                    and (perfil != "entregador" or request.form.get("ativo") != "on")
                    and db.session.scalar(
                        db.select(Entrega.id)
                        .where(
                            Entrega.entregador_id == obj.id,
                            Entrega.entregue_em.is_(None),
                        )
                        .limit(1)
                    )
                ):
                    abort(
                        409,
                        "Reatribua as entregas em andamento antes de desativar ou alterar este entregador.",
                    )
                obj.perfil = perfil
                obj.ativo = request.form.get("ativo") == "on"
                senha = request.form.get("senha", "")
                if senha or not obj.id:
                    if len(senha) < 10:
                        abort(400, "Use uma senha com pelo menos 10 caracteres.")
                    obj.senha = generate_password_hash(senha)
                if db.session.scalar(
                    db.select(Usuario).where(
                        Usuario.login == obj.login, Usuario.id != obj.id
                    )
                ):
                    abort(400, "Login já cadastrado.")
            if kind == "categorias" and db.session.scalar(
                db.select(Categoria).where(
                    Categoria.nome == obj.nome, Categoria.id != obj.id
                )
            ):
                abort(400, "Categoria já cadastrada.")
            db.session.add(obj)
            db.session.commit()
            return redirect(url_for("cadastros", kind=kind))
        edit = request.args.get("editar", type=int)
        if (
            kind == "usuarios"
            and edit
            and db.get_or_404(Usuario, edit).perfil == "cliente"
        ):
            abort(403)
        return render_template(
            "cadastros.html",
            kind=kind,
            rows=db.session.scalars(
                db.select(cls).where(
                    Usuario.perfil.in_(["admin", "garcom", "cozinha", "entregador"])
                )
                if kind == "usuarios"
                else db.select(cls).order_by(cls.id)
            ).all(),
            edit=db.get_or_404(cls, edit) if edit else None,
            categorias=db.session.scalars(db.select(Categoria)).all(),
        )

    @app.route("/caixa", methods=["GET", "POST"])
    @access("admin")
    def caixa():
        c = current_cash()
        if request.method == "POST":
            action = request.form.get("acao")
            # SQLite serializa as operações de caixa na mesma transação.
            db.session.rollback()
            db.session.execute(db.text("BEGIN IMMEDIATE"))
            c = current_cash()
            if action == "abrir":
                if c:
                    abort(409, "Já existe um caixa aberto.")
                db.session.add(Caixa(inicial=money(request.form.get("valor"))))
            elif action == "fechar":
                if not c:
                    abort(409, "Não existe caixa aberto.")
                c.fechado = datetime.now(timezone.utc)
                c.contado = money(request.form.get("valor"))
            elif action in ["sangria", "suprimento"]:
                if not c:
                    abort(409, "Abra o caixa.")
                valor = money(request.form.get("valor"))
                if valor <= 0:
                    abort(400, "Informe um valor maior que zero.")
                saldo = c.inicial + sum(
                    m.valor if m.tipo != "sangria" else -m.valor
                    for m in db.session.scalars(
                        db.select(Movimento).where(
                            Movimento.caixa_id == c.id, Movimento.forma == "dinheiro"
                        )
                    )
                )
                if action == "sangria" and valor > saldo:
                    abort(400, "Saldo em dinheiro insuficiente.")
                db.session.add(
                    Movimento(
                        caixa_id=c.id,
                        tipo=action,
                        forma="dinheiro",
                        valor=valor,
                        descricao=text("descricao", 200),
                    )
                )
            else:
                abort(400)
            db.session.commit()
            return redirect(url_for("caixa"))
        moves = (
            db.session.scalars(
                db.select(Movimento).where(Movimento.caixa_id == c.id)
            ).all()
            if c
            else []
        )
        saldo = (c.inicial if c else 0) + sum(
            m.valor if m.tipo != "sangria" else -m.valor
            for m in moves
            if m.forma == "dinheiro"
        )
        return render_template(
            "caixa.html",
            caixa=c,
            moves=moves,
            saldo=saldo,
            historico=db.session.scalars(
                db.select(Caixa).order_by(Caixa.id.desc()).limit(30)
            ).all(),
        )

    @app.get("/dashboard")
    @access("admin")
    def dashboard():
        tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(tz)
        start = (
            now.replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
        end = (
            (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
        orders = db.session.scalars(
            db.select(Pedido).where(Pedido.criado >= start, Pedido.criado < end)
        ).all()
        priority = {
            "pronto": 0,
            "em_preparo": 1,
            "aberto": 2,
            "saiu_entrega": 3,
            "entregue": 4,
        }
        orders.sort(key=lambda p: (p.pago, priority.get(p.status, 5), -p.id))
        return render_template(
            "dashboard.html",
            orders=orders,
            total=sum(p.total for p in orders),
            recebido=sum(p.total for p in orders if p.pago),
            pendentes=sum(not p.pago for p in orders),
        )

    return app


app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
