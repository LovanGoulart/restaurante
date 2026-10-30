"""Pedidos presenciais sem senha, isolados pela sessão aleatória do navegador."""

import hashlib
import json
import re
import secrets
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
from werkzeug.security import generate_password_hash
from models import db, Usuario, Categoria, Produto, Pedido, PedidoQR, EnvioPedido, Item
from orders_service import add_items, serialize_order
from notifications import emit_order
from customer_security import throttle

bp = Blueprint("salon_qr", __name__)


def salon_identifiers(data):
    # mesa era o campo legado da comanda; o contrato novo é explícito.
    comanda = data.get("comanda", data.get("mesa", ""))
    mesa = data.get("numero_mesa", "")
    if not isinstance(comanda, str) or not re.fullmatch(
        r"[0-9]{1,12}", comanda.strip()
    ):
        abort(400, "Informe o número da comanda (somente números, até 12 dígitos).")
    if not isinstance(mesa, str) or not re.fullmatch(r"[0-9]{1,12}", mesa.strip()):
        abort(400, "Informe o número da mesa (somente números, até 12 dígitos).")
    return str(int(comanda)), str(int(mesa))


def append_to_order(p, itens):
    if p.pago:
        abort(409, "Comanda já paga. Abra uma nova comanda.")
    add_items(p, itens)
    # Os itens antigos mantêm a etapa. Só os novos voltam para a cozinha.
    p.status = "aberto"


def guest_only():
    if not g.user or g.user.perfil != "visitante":
        abort(403, "Abra o cardápio pelo QR Code para continuar.")


def valid_table(value):
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[0-9]{1,12}", value.strip())
        or int(value.strip()) < 1
    ):
        raise ValueError(
            "Informe o número da sua mesa, somente com números, de 1 a 12 dígitos."
        )
    return str(int(value.strip()))


def session_table():
    try:
        return valid_table(session.get("qr_numero_mesa"))
    except ValueError:
        return None


@bp.route("/salao", methods=["GET", "POST"])
def enter():
    if g.user and g.user.perfil != "visitante":
        return render_template("qr_entrada.html", staff=True)
    if (
        g.user
        and request.method == "GET"
        and session_table()
        and request.args.get("editar") != "1"
    ):
        return redirect(url_for("salon_qr.menu"))
    values = dict(nome=g.user.nome if g.user else "", numero_mesa=session_table() or "")
    error = None
    if request.method == "POST":
        throttle("qr-entrada", 300, 3600)
        values = dict(
            nome=request.form.get("nome", "").strip(),
            numero_mesa=request.form.get("numero_mesa", "").strip(),
        )
        try:
            if not values["nome"] or len(values["nome"]) > 100:
                raise ValueError("Informe seu nome, com até 100 caracteres.")
            mesa = valid_table(values["numero_mesa"])
        except ValueError as exc:
            return (
                render_template(
                    "qr_entrada.html", staff=False, values=values, error=str(exc)
                ),
                400,
            )
        if g.user:
            user = g.user
            user.nome = values["nome"]
        else:
            user = Usuario(
                nome=values["nome"],
                login="qr_" + secrets.token_hex(24),
                senha=generate_password_hash(secrets.token_urlsafe(48)),
                perfil="visitante",
                ativo=True,
            )
            db.session.add(user)
        db.session.commit()
        if not g.user:
            session.clear()
        session["uid"] = user.id
        session["qr_numero_mesa"] = mesa
        return redirect(url_for("salon_qr.menu"))
    return render_template("qr_entrada.html", staff=False, values=values, error=error)


@bp.get("/salao/cardapio")
def menu():
    guest_only()
    if not session_table():
        return redirect(url_for("salon_qr.enter"))
    return render_template(
        "pdv.html",
        qr_customer=True,
        categorias=db.session.scalars(db.select(Categoria)).all(),
        produtos=db.session.scalars(
            db.select(Produto).where(Produto.ativo.is_(True))
        ).all(),
    )


@bp.get("/salao/meus-pedidos")
def my_orders():
    guest_only()
    return render_template("pedidos.html", customer=True)


@bp.route("/api/salao/pedidos", methods=["GET", "POST"])
def orders():
    guest_only()
    if request.method == "GET":
        rows = db.session.scalars(
            db.select(Pedido)
            .where(Pedido.qr.any(usuario_id=g.user.id))
            .order_by(Pedido.id.desc())
            .limit(100)
        ).all()
        return jsonify([serialize_order(p, g.user) for p in rows])
    throttle("qr-pedido:" + str(g.user.id), 30, 3600)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "Pedido inválido.")
    key = data.get("chave", "")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", key):
        abort(400, "Identificador inválido. Atualize a página.")
    fingerprint = hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    uid = g.user.id
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))
    old = db.session.scalar(
        db.select(EnvioPedido).where(
            EnvioPedido.usuario_id == uid, EnvioPedido.chave == key
        )
    )
    if old:
        if old.conteudo_hash != fingerprint:
            abort(409, "Envio já utilizado.")
        return jsonify(id=old.pedido_id, repetido=True)
    mesa = session_table()
    if not mesa:
        abort(
            409,
            "Informe seu nome e sua mesa na entrada do salão antes de enviar o pedido.",
        )
    p = Pedido(mesa="", numero_mesa=mesa, usuario_id=uid)
    add_items(p, data.get("itens"))
    for item in p.itens:
        item.visitante_id = uid
    p.qr.append(PedidoQR(usuario_id=uid))
    db.session.add(p)
    db.session.flush()
    db.session.add(
        EnvioPedido(
            usuario_id=uid, chave=key, conteudo_hash=fingerprint, pedido_id=p.id
        )
    )
    emit_order(p, "novo")
    db.session.commit()
    return jsonify(id=p.id), 201


@bp.post("/api/pedidos/<int:id>/comanda")
def assign(id):
    if not g.user or g.user.perfil not in {"admin", "garcom"}:
        abort(403)
    data = request.get_json(silent=True) or {}
    comanda, mesa = salon_identifiers(data)
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))
    p = db.get_or_404(Pedido, id)
    if p.online or not p.qr or p.pago:
        abort(409, "Este pedido não está disponível para vinculação.")
    if p.mesa:
        if p.mesa == comanda and p.numero_mesa == mesa:
            return jsonify(id=p.id)
        abort(
            409, "Pedido já vinculado. Não é possível trocar a comanda por este botão."
        )
    target = db.session.scalar(
        db.select(Pedido).where(
            Pedido.id != p.id,
            db.func.ltrim(Pedido.mesa, "0") == comanda.lstrip("0"),
            Pedido.mesa != "",
            Pedido.pago.is_(False),
            ~Pedido.online.has(),
        )
    )
    if target:
        if target.numero_mesa and target.numero_mesa != mesa:
            abort(409, "Esta comanda pertence a outra mesa.")
        target.numero_mesa = mesa
        list(target.itens)
        list(target.qr)
        for item in list(p.itens):
            p.itens.remove(item)
            target.itens.append(item)
        for link in list(p.qr):
            p.qr.remove(link)
            target.qr.append(link)
        db.session.execute(
            db.update(EnvioPedido)
            .where(EnvioPedido.pedido_id == p.id)
            .values(pedido_id=target.id)
        )
        from models import Notificacao

        db.session.execute(
            db.update(Notificacao)
            .where(Notificacao.pedido_id == p.id)
            .values(pedido_id=target.id)
        )
        db.session.delete(p)
        db.session.flush()
        # O status acompanha os itens ainda pendentes, sem perder itens já servidos.
        stages = {i.etapa for i in target.itens}
        target.status = next(
            (stage for stage in ["aberto", "em_preparo", "pronto"] if stage in stages),
            "entregue",
        )
        p = target
    else:
        p.mesa = comanda
        p.numero_mesa = mesa
    if data.get("entregar") is True:
        if p.status != "pronto":
            abort(409, "Marque a entrega somente quando o pedido estiver pronto.")
        p.status = "entregue"
        for i in p.itens:
            if i.etapa == "pronto":
                i.etapa = "entregue"
        emit_order(p, "entregue")
    else:
        emit_order(p, "vinculado")
    db.session.commit()
    return jsonify(id=p.id)


@bp.get("/qr-code")
def qr_page():
    if not g.user or g.user.perfil != "admin":
        abort(403)
    return render_template(
        "qr_code.html", link=url_for("salon_qr.enter", _external=True)
    )


@bp.get("/qr-code.svg")
def qr_image():
    if not g.user or g.user.perfil != "admin":
        abort(403)
    import io
    import qrcode
    import qrcode.image.svg
    from flask import Response

    image = qrcode.make(
        url_for("salon_qr.enter", _external=True),
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=8,
        border=4,
    )
    output = io.BytesIO()
    image.save(output)
    return Response(output.getvalue(), mimetype="image/svg+xml")
