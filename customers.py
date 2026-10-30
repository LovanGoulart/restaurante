import hashlib, json, re
from functools import wraps
from flask import (
    Blueprint,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import IntegrityError
from models import (
    db,
    Usuario,
    Cliente,
    Loja,
    Categoria,
    Produto,
    Pedido,
    PedidoOnline,
    EnvioPedido,
)
from werkzeug.security import generate_password_hash
from customer_security import (
    cpf_valido,
    cpf_digits,
    data_nascimento,
    encode_cpf,
    throttle,
)
from orders_service import add_items, serialize_order
from notifications import emit_order

bp = Blueprint("customers", __name__)


def role(*roles):
    def deco(fn):
        @wraps(fn)
        def wrap(*args, **kwargs):
            if not g.user:
                return (
                    (jsonify(error="Entre na sua conta para continuar."), 401)
                    if request.path.startswith("/api")
                    else redirect(url_for("login", next=request.path))
                )
            if g.user.perfil not in roles:
                abort(403)
            return fn(*args, **kwargs)

        return wrap

    return deco


def store():
    return db.session.get(Loja, 1) or Loja(
        id=1,
        nome="Restaurante Manager",
        taxa_entrega=0,
        entrega_ativa=True,
        pedidos_ativos=True,
    )


def profile():
    c = db.session.scalar(db.select(Cliente).where(Cliente.usuario_id == g.user.id))
    if not c:
        abort(409, "Cadastro do cliente incompleto.")
    return c


def clean(data, name, maxlen, required=False):
    value = data.get(name, "")
    if not isinstance(value, str):
        raise ValueError("Campo inválido: " + name)
    value = value.strip()
    if len(value) > maxlen or required and not value:
        raise ValueError("Preencha corretamente: " + name)
    return value


def address(data, required):
    return {
        key: clean(data, key, size, required)
        for key, size in [
            ("endereco", 160),
            ("bairro", 100),
            ("numero", 20),
            ("referencia", 200),
        ]
    }


def money(value):
    from decimal import Decimal, InvalidOperation

    try:
        v = Decimal(str(value).replace(",", "."))
        if not v.is_finite() or v < 0 or v > 1000000 or v.as_tuple().exponent < -2:
            raise ValueError()
        return int(v * 100)
    except (InvalidOperation, ValueError):
        raise ValueError("Valor monetário inválido.")


@bp.get("/cardapio")
def menu():
    if g.user and g.user.perfil == "visitante":
        return redirect(url_for("salon_qr.menu"))
    if g.user and g.user.perfil == "entregador":
        return redirect(url_for("couriers.deliveries"))
    if g.user and g.user.perfil in ["garcom", "cozinha"]:
        return redirect(
            url_for("pdv") if g.user.perfil == "garcom" else url_for("pedidos")
        )
    c = profile() if g.user and g.user.perfil == "cliente" else None
    return render_template(
        "cardapio.html",
        loja=store(),
        cliente=c,
        categorias=db.session.scalars(db.select(Categoria)).all(),
        produtos=db.session.scalars(
            db.select(Produto).where(Produto.ativo.is_(True))
        ).all(),
    )


@bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("home"))
    error = None
    values = {}
    if request.method == "POST":
        throttle("cadastro", 10, 3600)
        # Senha e CPF não são devolvidos para o HTML após erros.
        values = {
            k: request.form.get(k, "")
            for k in [
                "nome",
                "login",
                "nascimento",
                "modalidade",
                "endereco",
                "bairro",
                "numero",
                "referencia",
                "telefone",
            ]
        }
        try:
            nome = clean(request.form, "nome", 100, True)
            login = clean(request.form, "login", 80, True)
            if not re.fullmatch(r"[A-Za-z0-9_.@+\-]{3,80}", login):
                raise ValueError("Use um login com 3 a 80 letras, números ou . _ @ + -")
            senha = request.form.get("senha", "")
            if not 10 <= len(senha) <= 128 or senha != request.form.get(
                "confirmar_senha"
            ):
                raise ValueError(
                    "As senhas devem coincidir e ter de 10 a 128 caracteres."
                )
            cpf = request.form.get("cpf", "")
            if not cpf_valido(cpf):
                raise ValueError("CPF inválido. Confira os 11 dígitos.")
            nascimento = data_nascimento(request.form.get("nascimento"))
            modalidade = request.form.get("modalidade", "retirada")
            if modalidade not in ["retirada", "entrega"]:
                raise ValueError("Selecione retirada ou entrega.")
            addr = (
                address(request.form, modalidade == "entrega")
                if modalidade == "entrega"
                else dict(endereco="", bairro="", numero="", referencia="")
            )
            telefone = clean(request.form, "telefone", 25)
            cifrado, digest = encode_cpf(cpf_digits(cpf))
            if db.session.scalar(
                db.select(Usuario.id).where(Usuario.login == login)
            ) or db.session.scalar(
                db.select(Cliente.id).where(Cliente.cpf_hash == digest)
            ):
                raise ValueError(
                    "Não foi possível cadastrar com estes dados. Verifique login e CPF."
                )
            user = Usuario(
                nome=nome,
                login=login,
                senha=generate_password_hash(senha),
                perfil="cliente",
                ativo=True,
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(
                Cliente(
                    usuario_id=user.id,
                    cpf_cifrado=cifrado,
                    cpf_hash=digest,
                    cpf_final=cpf_digits(cpf)[-2:],
                    nascimento=nascimento,
                    telefone=telefone,
                    **addr,
                )
            )
            db.session.commit()
            session.clear()
            session["uid"] = user.id
            return redirect(url_for("customers.menu"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            error = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Não foi possível cadastrar com estes dados. Verifique login e CPF."
            )
    return render_template("cadastro_cliente.html", error=error, values=values)


@bp.route("/minha-conta", methods=["GET", "POST"])
@role("cliente")
def account():
    c = profile()
    error = None
    saved = False
    if request.method == "POST":
        try:
            nome = clean(request.form, "nome", 100, True)
            telefone = clean(request.form, "telefone", 25)
            modalidade = request.form.get("modalidade", "retirada")
            if modalidade not in ["entrega", "retirada"]:
                raise ValueError("Modalidade inválida.")
            addr = (
                address(request.form, True)
                if modalidade == "entrega"
                else {
                    k: getattr(c, k)
                    for k in ["endereco", "bairro", "numero", "referencia"]
                }
            )
            g.user.nome = nome
            c.telefone = telefone if modalidade == "entrega" else c.telefone
            for k, v in addr.items():
                setattr(c, k, v)
            senha = request.form.get("senha", "")
            if senha:
                from werkzeug.security import check_password_hash

                if not check_password_hash(
                    g.user.senha, request.form.get("senha_atual", "")
                ):
                    raise ValueError("Senha atual incorreta.")
                if not 10 <= len(senha) <= 128 or senha != request.form.get(
                    "confirmar_senha"
                ):
                    raise ValueError(
                        "Confira a confirmação da nova senha (10 a 128 caracteres)."
                    )
                g.user.senha = generate_password_hash(senha)
            db.session.commit()
            saved = True
        except ValueError as exc:
            db.session.rollback()
            error = str(exc)
    return render_template("minha_conta.html", cliente=c, error=error, saved=saved)


@bp.get("/meus-pedidos")
@role("cliente")
def my_orders():
    return render_template("pedidos.html", customer=True)


@bp.get("/api/cliente/pedidos")
@role("cliente")
def list_orders():
    orders = db.session.scalars(
        db.select(Pedido)
        .where(Pedido.usuario_id == g.user.id, Pedido.online.has())
        .order_by(Pedido.id.desc())
        .limit(200)
    ).all()
    return jsonify([serialize_order(p, g.user) for p in orders])


@bp.post("/api/cliente/pedidos")
@role("cliente")
def place_order():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        abort(400, "Pedido inválido.")
    token = d.get("chave", "")
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", token):
        abort(400, "Identificador do envio inválido. Atualize a página.")
    fingerprint = hashlib.sha256(
        json.dumps(
            d, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    # Uma chave por tentativa garante que um retry não crie outro pedido.
    uid = g.user.id
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))
    old = db.session.scalar(
        db.select(EnvioPedido).where(
            EnvioPedido.usuario_id == uid, EnvioPedido.chave == token
        )
    )
    if old:
        if old.conteudo_hash != fingerprint:
            abort(
                409,
                "Este envio já foi usado. Confira seus pedidos antes de iniciar outro.",
            )
        return jsonify(id=old.pedido_id, repetido=True), 200
    loja = store()
    if not loja.pedidos_ativos:
        abort(409, "Os pedidos online estão pausados neste momento.")
    modalidade = d.get("modalidade")
    forma = d.get("forma_pagamento")
    if modalidade not in ["retirada", "entrega"]:
        abort(400, "Escolha retirada ou entrega.")
    if modalidade == "entrega" and not loja.entrega_ativa:
        abort(409, "A entrega está indisponível. Escolha retirada no caixa.")
    if forma not in ["pix", "dinheiro", "credito", "debito"]:
        abort(400, "Escolha a forma de pagamento.")
    c = profile()
    try:
        addr = (
            address(d, True)
            if modalidade == "entrega"
            else dict(endereco="", bairro="", numero="", referencia="")
        )
        telefone = clean(d, "telefone", 25) if modalidade == "entrega" else ""
        troco = (
            money(d["troco_para"])
            if forma == "dinheiro" and d.get("troco_para") not in [None, ""]
            else None
        )
    except ValueError as exc:
        abort(400, str(exc))
    p = Pedido(mesa="Online", usuario_id=uid)
    p.online = PedidoOnline(
        cliente_id=c.id,
        modalidade=modalidade,
        destinatario=g.user.nome,
        telefone=telefone,
        forma_pagamento=forma,
        troco_para=troco,
        taxa_entrega=loja.taxa_entrega if modalidade == "entrega" else 0,
        **addr,
    )
    add_items(p, d.get("itens"))
    if d.get("total_previsto") is not None and (
        type(d["total_previsto"]) is not int or d["total_previsto"] != p.total
    ):
        abort(
            409, "Os preços ou a taxa mudaram. Atualize o cardápio antes de confirmar."
        )
    if troco is not None and troco < p.total:
        abort(400, "O valor para troco deve ser igual ou maior que o total do pedido.")
    db.session.add(p)
    db.session.flush()
    db.session.add(
        EnvioPedido(
            usuario_id=uid, chave=token, conteudo_hash=fingerprint, pedido_id=p.id
        )
    )
    if modalidade == "entrega":
        for k, v in addr.items():
            setattr(c, k, v)
        c.telefone = telefone
    emit_order(p, "novo")
    db.session.commit()
    return jsonify(id=p.id), 201


@bp.get("/api/cliente/envios/<chave>")
@role("cliente")
def sent_attempt(chave):
    if len(chave) > 80:
        abort(400, "Envio inválido.")
    envio = db.session.scalar(
        db.select(EnvioPedido).where(
            EnvioPedido.usuario_id == g.user.id, EnvioPedido.chave == chave
        )
    )
    return jsonify(id=envio.pedido_id if envio else None)


@bp.route("/loja", methods=["GET", "POST"])
@role("admin")
def settings():
    loja = store()
    error = None
    if request.method == "POST":
        try:
            nome = clean(request.form, "nome", 100, True)
            taxa = money(request.form.get("taxa_entrega"))
            loja.nome = nome
            loja.taxa_entrega = taxa
            loja.entrega_ativa = request.form.get("entrega_ativa") == "on"
            loja.pedidos_ativos = request.form.get("pedidos_ativos") == "on"
            db.session.add(loja)
            db.session.commit()
            return redirect(url_for("customers.settings", salvo=1))
        except ValueError as exc:
            db.session.rollback()
            error = str(exc)
    return render_template("loja.html", loja=loja, error=error)


@bp.route("/clientes", methods=["GET", "POST"])
@role("admin")
def clients():
    if request.method == "POST":
        id = request.form.get("id", type=int)
        c = db.get_or_404(Cliente, id)
        c.usuario.ativo = request.form.get("ativo") == "on"
        db.session.commit()
        return redirect(url_for("customers.clients"))
    return render_template(
        "clientes.html",
        clientes=db.session.scalars(
            db.select(Cliente).order_by(Cliente.id.desc()).limit(200)
        ).all(),
    )
