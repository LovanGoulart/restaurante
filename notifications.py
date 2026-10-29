"""Eventos persistidos na mesma transação da operação e outbox de Web Push."""

import base64

import json

import time

from datetime import datetime

from urllib.parse import urlsplit

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    g,
    jsonify,
    request,
    session,
    stream_with_context,
)

from sqlalchemy import update

from models import db, Notificacao, PushSubscription, PushDelivery, Usuario

from config import DATA

bp = Blueprint("notifications", __name__)


def emit_order(pedido, tipo):

    users = db.session.scalars(db.select(Usuario).where(Usuario.ativo.is_(True))).all()

    titles = {
        "atribuida": "Nova entrega atribuída",
        "novo": "Novo pedido na cozinha",
        "em_preparo": "Preparo iniciado",
        "pronto": "Pedido pronto para retirar",
        "entregue": "Pedido entregue",
        "saiu_entrega": "Pedido saiu para entrega",
        "pago": "Pagamento registrado",
    }

    for u in users:

        is_driver = bool(
            u.perfil == "entregador"
            and pedido.online
            and pedido.online.modalidade == "entrega"
            and pedido.entrega
            and pedido.entrega.entregador_id == u.id
        )

        if tipo == "atribuida" and not (u.perfil == "admin" or is_driver):

            continue

        if not (
            u.perfil == "admin"
            or u.id == pedido.usuario_id
            or u.perfil == "cozinha"
            and tipo != "pago"
            or u.perfil == "garcom"
            and not pedido.online
            or is_driver
        ):

            continue

        if u.perfil == "garcom" and pedido.online:

            continue

        alerta_cliente = (
            u.perfil == "cliente"
            and u.id == pedido.usuario_id
            and tipo
            in [
                "novo",
                "em_preparo",
                "pronto",
                "saiu_entrega",
                "entregue",
                "pago",
            ]
        )

        alerta = (
            alerta_cliente
            or (is_driver and tipo in ["saiu_entrega", "atribuida"])
            or (tipo == "saiu_entrega" and u.id == pedido.usuario_id)
            or (tipo == "pronto" and (u.id == pedido.usuario_id or u.perfil == "admin"))
            or (tipo == "novo" and u.perfil in ["cozinha", "admin"])
        )

        label = (
            (
                "Entrega"
                if pedido.online.modalidade == "entrega"
                else "Retirada no caixa"
            )
            if pedido.online
            else "Mesa " + pedido.mesa
        )

        title = "Pedido pronto" if pedido.online and tipo == "pronto" else titles[tipo]

        if u.perfil == "cliente":
            title = {
                "novo": "Seu pedido foi recebido!",
                "em_preparo": "Seu pedido está em preparo!",
                "pronto": "Seu pedido está pronto!",
                "saiu_entrega": "Seu pedido saiu para entrega!",
                "entregue": "Seu pedido foi entregue!",
                "pago": "Pagamento do seu pedido confirmado!",
            }.get(tipo, title)

        n = Notificacao(
            usuario_id=u.id,
            pedido_id=pedido.id,
            titulo=title,
            mensagem=f"{label} · Pedido #{pedido.id}",
            tipo=tipo,
            alerta=alerta,
        )

        db.session.add(n)

        db.session.flush()

        if alerta:

            for sub in db.session.scalars(
                db.select(PushSubscription).where(
                    PushSubscription.usuario_id == u.id,
                    PushSubscription.ativo.is_(True),
                )
            ):

                db.session.add(
                    PushDelivery(notificacao_id=n.id, subscription_id=sub.id)
                )


def as_dict(n):

    return dict(
        id=n.id,
        titulo=n.titulo,
        mensagem=n.mensagem,
        tipo=n.tipo,
        alerta=n.alerta,
        lida=n.lida,
        pedido_id=n.pedido_id,
        criado=n.criado.isoformat() + "Z",
        url=(
            (
                "/entregas"
                if g.user.perfil == "entregador"
                else "/meus-pedidos" if g.user.perfil == "cliente" else "/pedidos"
            )
            + "?pedido="
            + str(n.pedido_id)
        ),
    )


@bp.before_request
def auth():

    if not g.user:

        return jsonify(error="Faça login novamente."), 401


@bp.get("/api/notificacoes")
def inbox():

    q = db.select(Notificacao).where(
        Notificacao.usuario_id == g.user.id, Notificacao.alerta.is_(True)
    )

    rows = db.session.scalars(q.order_by(Notificacao.id.desc()).limit(30)).all()

    unread = db.session.scalar(
        db.select(db.func.count())
        .select_from(Notificacao)
        .where(
            Notificacao.usuario_id == g.user.id,
            Notificacao.lida.is_(False),
            Notificacao.alerta.is_(True),
        )
    )

    return jsonify(items=[as_dict(n) for n in rows], nao_lidas=unread)


@bp.post("/api/notificacoes/lidas")
def read():

    data = request.get_json(silent=True) or {}

    ate = data.get("ate")

    if type(ate) is not int or ate < 0:

        abort(400, "Notificação inválida.")

    db.session.execute(
        update(Notificacao)
        .where(Notificacao.usuario_id == g.user.id, Notificacao.id <= ate)
        .values(lida=True)
    )

    db.session.commit()

    return jsonify(ok=True)


@bp.get("/api/eventos")
def events():

    uid = g.user.id

    raw = request.headers.get("Last-Event-ID") or request.args.get("after", "0")

    try:

        cursor = max(0, int(raw))

    except (ValueError, TypeError):

        abort(400, "Cursor inválido.")

    # A conexão termina a cada 25 s para revalidar a sessão na reconexão.

    def generate():

        nonlocal cursor

        try:

            yield "retry: 2000\nevent: connected\ndata: {}\n\n"

            deadline = time.monotonic() + current_app.config.get("SSE_DURATION", 25)

            while time.monotonic() < deadline:

                user = db.session.get(Usuario, uid)

                if not user or not user.ativo:

                    return

                rows = db.session.scalars(
                    db.select(Notificacao)
                    .where(Notificacao.usuario_id == uid, Notificacao.id > cursor)
                    .order_by(Notificacao.id)
                    .limit(100)
                ).all()

                payload = [as_dict(n) for n in rows]

                db.session.remove()  # não manter transação SQLite aberta durante a espera

                for item in payload:

                    cursor = item["id"]

                    yield f"id: {cursor}\nevent: pedido\ndata: {json.dumps(item,ensure_ascii=False)}\n\n"

                yield ": heartbeat\n\n"

                time.sleep(current_app.config.get("SSE_INTERVAL", 1))

        finally:

            db.session.remove()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )


def push_config():

    path = DATA / "vapid.json"

    if not path.exists():

        return None

    try:

        return json.loads(path.read_text())

    except (ValueError, OSError):

        return None


def worker_online():

    try:

        return time.time() - (DATA / "push-worker.heartbeat").stat().st_mtime < 90

    except OSError:

        return False


@bp.get("/api/push/config")
def config():

    c = push_config()

    return jsonify(
        available=bool(c and worker_online()),
        public_key=c.get("public_key") if c else None,
    )


def validate_subscription(data):

    if not isinstance(data, dict):

        abort(400, "Inscrição inválida.")

    endpoint = data.get("endpoint", "")

    if not isinstance(endpoint, str) or len(endpoint) > 2048:

        abort(400, "Endereço push inválido.")

    try:

        u = urlsplit(endpoint)

        port = u.port

    except ValueError:

        abort(400, "Endereço push inválido.")

    host = (u.hostname or "").lower()

    # Somente serviços push dos navegadores, impedindo destinos arbitrários/SSRF.

    allowed = (
        host == "fcm.googleapis.com"
        or host.endswith(".push.services.mozilla.com")
        or host.endswith(".notify.windows.com")
        or host == "web.push.apple.com"
    )

    if (
        u.scheme != "https"
        or u.username
        or u.password
        or port not in [None, 443]
        or not allowed
        or u.fragment
    ):

        abort(400, "Provedor push não permitido.")

    keys = data.get("keys")

    if not isinstance(keys, dict):

        abort(400, "Chaves push inválidas.")

    for name, size in [("p256dh", 65), ("auth", 16)]:

        value = keys.get(name, "")

        try:

            if not isinstance(value, str) or len(value) > 160:

                raise ValueError()

            decoded = base64.b64decode(
                value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
            )

            if len(decoded) != size or name == "p256dh" and decoded[0] != 4:

                raise ValueError()

        except (ValueError, TypeError):

            abort(400, "Chaves push inválidas.")

    return endpoint, keys


@bp.post("/api/push/subscribe")
def subscribe():

    if not push_config() or not worker_online():

        abort(
            409, "Push indisponível. Configure o serviço de notificações no servidor."
        )

    endpoint, keys = validate_subscription(request.get_json(silent=True))

    sub = db.session.scalar(
        db.select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )

    if not sub:

        sub = PushSubscription(endpoint=endpoint)

        db.session.add(sub)

    elif sub.usuario_id != g.user.id:

        db.session.execute(
            update(PushDelivery)
            .where(
                PushDelivery.subscription_id == sub.id,
                PushDelivery.estado == "pendente",
            )
            .values(estado="cancelado")
        )

    sub.usuario_id = g.user.id

    sub.p256dh = keys["p256dh"]

    sub.auth = keys["auth"]

    sub.ativo = True

    session["push_endpoint"] = endpoint

    db.session.commit()

    return jsonify(ok=True)


@bp.post("/api/push/unsubscribe")
def unsubscribe():

    endpoint = (request.get_json(silent=True) or {}).get("endpoint") or session.get(
        "push_endpoint"
    )

    if endpoint:

        db.session.execute(
            update(PushSubscription)
            .where(
                PushSubscription.usuario_id == g.user.id,
                PushSubscription.endpoint == endpoint,
            )
            .values(ativo=False)
        )

        db.session.commit()

    session.pop("push_endpoint", None)

    return jsonify(ok=True)
