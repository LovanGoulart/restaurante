"""Tele-entregas atribuídas e conferência dos recebimentos pelo administrador."""

from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, g, jsonify, render_template, request
from sqlalchemy import update, or_
from models import (
    db,
    Usuario,
    Pedido,
    PedidoOnline,
    Entrega,
    Caixa,
    Movimento,
    Notificacao,
)
from customers import role
from orders_service import serialize_order
from notifications import emit_order

bp = Blueprint("couriers", __name__)
FORMS = ["dinheiro", "pix", "credito", "debito"]


def now():
    return datetime.now(timezone.utc)


def day_range(value):
    tz = ZoneInfo("America/Sao_Paulo")
    try:
        day = date.fromisoformat(value) if value else datetime.now(tz).date()
    except (ValueError, TypeError):
        abort(400, "Data inválida.")
    start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    return (
        day,
        start.astimezone(timezone.utc).replace(tzinfo=None),
        (start + timedelta(days=1)).astimezone(timezone.utc).replace(tzinfo=None),
    )


def json_data():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        abort(400, "Dados inválidos.")
    return d


def lock():
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))


def receipt(e):
    return dict(
        id=e.id,
        entregador_id=e.entregador_id,
        entregador=e.entregador.nome,
        entregue_em=e.entregue_em.isoformat() + "Z" if e.entregue_em else None,
        forma_pagamento=e.forma_pagamento,
        valor_pedido=e.valor_pedido,
        valor_recebido=e.valor_recebido,
        pago_antecipado=e.pago_antecipado,
        acertado=bool(e.acertado_em),
        acertado_em=e.acertado_em.isoformat() + "Z" if e.acertado_em else None,
    )


@bp.get("/api/entregadores")
@role("admin")
def drivers():
    users = db.session.scalars(
        db.select(Usuario)
        .where(Usuario.perfil == "entregador", Usuario.ativo.is_(True))
        .order_by(Usuario.nome)
    ).all()
    return jsonify([dict(id=u.id, nome=u.nome) for u in users])


@bp.post("/api/pedidos/<int:id>/entregador")
@role("admin")
def assign(id):
    d = json_data()
    uid = d.get("entregador_id")
    if type(uid) is not int:
        abort(400, "Selecione um entregador.")
    lock()
    p = db.get_or_404(Pedido, id)
    u = db.session.get(Usuario, uid)
    if not p.online or p.online.modalidade != "entrega":
        abort(400, "Somente tele-entregas podem ser atribuídas.")
    if p.status not in ["pronto", "saiu_entrega"]:
        abort(409, "O pedido precisa estar pronto ou em entrega.")
    if not u or not u.ativo or u.perfil != "entregador":
        abort(400, "Entregador inválido ou inativo.")
    e = p.entrega
    if e and e.entregue_em:
        abort(409, "Entrega já concluída.")
    if e and e.entregador_id == uid and p.status == "saiu_entrega":
        return jsonify(ok=True)
    if e:
        previous = e.entregador_id
        if previous != uid:
            db.session.add(
                Notificacao(
                    usuario_id=previous,
                    pedido_id=p.id,
                    titulo="Entrega reatribuída",
                    mensagem=f"Pedido #{p.id} foi atribuído a outro entregador.",
                    tipo="reatribuida",
                    alerta=False,
                )
            )
        e.entregador_id = uid
        e.atribuido_em = now()
    else:
        e = Entrega(pedido=p, entregador_id=uid)
        db.session.add(e)
    changed = p.status != "saiu_entrega"
    p.status = "saiu_entrega"
    db.session.flush()
    emit_order(p, "saiu_entrega" if changed else "atribuida")
    db.session.commit()
    return jsonify(ok=True)


@bp.get("/entregas")
@role("entregador")
def deliveries():
    return render_template("entregas.html")


@bp.get("/api/entregas")
@role("entregador")
def list_deliveries():
    day, start, end = day_range(request.args.get("data"))
    # As entregas em andamento continuam visíveis mesmo se iniciadas no dia anterior.
    q = (
        db.select(Entrega)
        .join(Pedido)
        .join(PedidoOnline)
        .where(
            Entrega.entregador_id == g.user.id,
            PedidoOnline.modalidade == "entrega",
            or_(
                Entrega.entregue_em.is_(None),
                (Entrega.entregue_em >= start) & (Entrega.entregue_em < end),
            ),
        )
        .order_by(Entrega.id.desc())
    )
    rows = db.session.scalars(q).all()
    requested = request.args.get("pedido", type=int)
    if requested and not any(e.pedido_id == requested for e in rows):
        extra = db.session.scalar(
            db.select(Entrega).where(
                Entrega.pedido_id == requested, Entrega.entregador_id == g.user.id
            )
        )
        if (
            extra
            and extra.pedido.online
            and extra.pedido.online.modalidade == "entrega"
        ):
            rows.insert(0, extra)
    result = []
    for e in rows:
        item = serialize_order(e.pedido, g.user)
        item["recebimento"] = receipt(e)
        result.append(item)
    return jsonify(data=day.isoformat(), items=result)


@bp.post("/api/entregas/<int:id>/concluir")
@role("entregador")
def complete(id):
    d = json_data()
    lock()
    e = db.get_or_404(Entrega, id)
    p = e.pedido
    if e.entregador_id != g.user.id:
        abort(403)
    if not p.online or p.online.modalidade != "entrega":
        abort(403)
    if e.entregue_em or p.status != "saiu_entrega":
        abort(409, "Esta entrega já foi concluída ou mudou de status.")
    if d.get("confirmado") is not True:
        abort(400, "Confirme a entrega e o recebimento antes de concluir.")
    # Pagamento registrado antes da conclusão não deve ser cobrado novamente.
    e.pago_antecipado = p.pago
    e.valor_pedido = p.total
    if p.pago:
        movimento = db.session.scalar(
            db.select(Movimento).where(Movimento.pedido_id == p.id)
        )
        e.forma_pagamento = movimento.forma if movimento else "antecipado"
        e.valor_recebido = 0
    else:
        forma = d.get("forma_pagamento")
        if forma not in FORMS:
            abort(400, "Informe a forma de pagamento efetivamente recebida.")
        e.forma_pagamento = forma
        e.valor_recebido = p.total
    e.entregue_em = now()
    p.status = "entregue"
    # Não há movimento de caixa até a conferência do administrador.
    emit_order(p, "entregue")
    db.session.commit()
    return jsonify(ok=True, recebimento=receipt(e))


@bp.get("/acerto-entregadores")
@role("admin")
def settlement():
    return render_template("acerto_entregadores.html")


@bp.get("/api/acerto-entregadores")
@role("admin")
def settlement_data():
    day, start, end = day_range(request.args.get("data"))
    raw = request.args.get("entregador_id")
    uid = None
    if raw:
        try:
            uid = int(raw)
        except ValueError:
            abort(400, "Entregador inválido.")
    query = (
        db.select(Entrega)
        .where(Entrega.entregue_em >= start, Entrega.entregue_em < end)
        .order_by(Entrega.entregue_em.desc())
    )
    if uid:
        query = query.where(Entrega.entregador_id == uid)
    rows = db.session.scalars(query).all()
    groups = {}
    items = []
    for e in rows:
        group = groups.setdefault(
            e.entregador_id,
            dict(
                id=e.entregador_id,
                nome=e.entregador.nome,
                entregas=0,
                total_pedidos=0,
                antecipado=0,
                a_conferir=0,
                recebido_total=0,
                conferido=0,
                dinheiro_repassar=0,
                formas={f: 0 for f in FORMS},
                pendentes=0,
            ),
        )
        group["entregas"] += 1
        group["total_pedidos"] += e.valor_pedido
        group["recebido_total"] += e.valor_recebido
        if e.acertado_em:
            group["conferido"] += e.valor_recebido
        if e.pago_antecipado:
            group["antecipado"] += e.valor_pedido
        if not e.acertado_em:
            group["pendentes"] += 1
            group["a_conferir"] += e.valor_recebido
            if e.forma_pagamento in FORMS:
                group["formas"][e.forma_pagamento] += e.valor_recebido
            if e.forma_pagamento == "dinheiro":
                group["dinheiro_repassar"] += e.valor_recebido
        items.append(
            dict(
                **receipt(e),
                pedido_id=e.pedido_id,
                cliente=e.pedido.online.destinatario,
            )
        )
    # Mantém no filtro entregadores inativos e perfis antigos com histórico de entregas.
    all_users = db.session.scalars(
        db.select(Usuario)
        .where(
            or_(
                Usuario.perfil == "entregador",
                Usuario.id.in_(db.select(Entrega.entregador_id)),
            )
        )
        .order_by(Usuario.nome)
    ).all()
    return jsonify(
        data=day.isoformat(),
        resumo=list(groups.values()),
        items=items,
        entregadores=[dict(id=u.id, nome=u.nome) for u in all_users],
    )


@bp.post("/api/acerto-entregadores")
@role("admin")
def settle():
    d = json_data()
    ids = d.get("entregas")
    if d.get("confirmado") is not True:
        abort(400, "Confirme o recebimento do dinheiro e a conferência dos pagamentos.")
    if (
        not isinstance(ids, list)
        or not 1 <= len(ids) <= 500
        or any(type(id) is not int for id in ids)
        or len(set(ids)) != len(ids)
    ):
        abort(400, "Selecione entregas válidas.")
    lock()
    rows = db.session.scalars(db.select(Entrega).where(Entrega.id.in_(ids))).all()
    if len(rows) != len(ids) or any(not e.entregue_em or e.acertado_em for e in rows):
        abort(
            409,
            "Uma das entregas não está mais disponível para conferência. Atualize a tela.",
        )
    caixa = db.session.scalar(db.select(Caixa).where(Caixa.fechado.is_(None)))
    if not caixa and any(not e.pago_antecipado for e in rows):
        abort(409, "Abra o caixa antes de registrar o acerto.")
    at = now()
    for e in rows:
        p = e.pedido
        if not e.pago_antecipado:
            if p.pago or db.session.scalar(
                db.select(Movimento.id).where(Movimento.pedido_id == p.id)
            ):
                abort(409, "Um pedido já tem pagamento registrado. Atualize a tela.")
            p.pago = True
            m = Movimento(
                caixa_id=caixa.id,
                pedido_id=p.id,
                tipo="recebimento",
                forma=e.forma_pagamento,
                valor=e.valor_recebido,
                descricao=f"Acerto entregador {e.entregador.nome[:80]} · pedido #{p.id}",
            )
            db.session.add(m)
            db.session.flush()
            e.movimento_id = m.id
            from fiscal_service import enqueue

            enqueue(p, e.forma_pagamento)
            emit_order(p, "pago")
        e.acertado_em = at
        e.acertado_por_id = g.user.id
    db.session.commit()
    return jsonify(ok=True, conferidas=len(rows))
