"""Histórico administrativo usando datas já registradas, sem alterar o banco."""
from datetime import datetime, time, timedelta, timezone, date
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, render_template, request, url_for
from sqlalchemy import union_all, or_, and_
from models import db, Pedido, Movimento, Entrega, Notificacao
from customers import role

bp = Blueprint("order_history", __name__)
LOCAL_ZONE = ZoneInfo("America/Sao_Paulo")
PAGE_SIZE = 50


def local_today():
    return datetime.now(LOCAL_ZONE).date()


def day_bounds(day):
    # Comparação em UTC, como os timestamps SQLite do sistema.
    start = datetime.combine(day, time.min, LOCAL_ZONE)
    end = datetime.combine(day + timedelta(days=1), time.min, LOCAL_ZONE)
    return (start.astimezone(timezone.utc).replace(tzinfo=None),
            end.astimezone(timezone.utc).replace(tzinfo=None))


def completion_dates():
    # Finalização ocorre na última etapa: entrega/retirada ou pagamento.
    # Para registros antigos sem esses eventos, usa a criação como referência.
    events = union_all(
        db.select(Pedido.id.label("pedido_id"), Pedido.criado.label("momento")),
        db.select(Movimento.pedido_id, Movimento.criado).where(Movimento.tipo == "recebimento"),
        db.select(Entrega.pedido_id, Entrega.entregue_em).where(Entrega.entregue_em.is_not(None)),
        db.select(Notificacao.pedido_id, Notificacao.criado).where(
            Notificacao.tipo.in_(["pago", "entregue"])),
    ).subquery()
    return db.select(events.c.pedido_id, db.func.max(events.c.momento).label("finalizado_em")).group_by(
        events.c.pedido_id).subquery()


def current_admin_orders(query):
    dates = completion_dates()
    start, end = day_bounds(local_today())
    return query.outerjoin(dates, dates.c.pedido_id == Pedido.id).where(or_(
        Pedido.pago.is_(False), Pedido.status != "entregue",
        and_(dates.c.finalizado_em >= start, dates.c.finalizado_em < end)))


@bp.get("/pedidos/finalizados")
@role("admin")
def page():
    chosen = request.args.get("data", "").strip()
    all_dates = request.args.get("todas") == "1" and not chosen
    if not chosen and not all_dates:
        chosen = local_today().isoformat()
    day = None
    if chosen:
        try:
            day = date.fromisoformat(chosen)
            if day.isoformat() != chosen or day == date.max:
                raise ValueError()
        except ValueError:
            abort(400, "Escolha uma data válida no formato AAAA-MM-DD.")
    raw_page = request.args.get("pagina", "1")
    if not raw_page.isascii() or not raw_page.isdigit() or not 1 <= int(raw_page) <= 1000000:
        abort(400, "Página inválida.")
    page_number = int(raw_page)
    dates = completion_dates()
    query = db.select(Pedido, dates.c.finalizado_em).join(dates, dates.c.pedido_id == Pedido.id).where(
        Pedido.pago.is_(True), Pedido.status == "entregue")
    if day:
        start, end = day_bounds(day)
        query = query.where(dates.c.finalizado_em >= start, dates.c.finalizado_em < end)
    rows = db.session.execute(query.order_by(dates.c.finalizado_em.desc(), Pedido.id.desc()).offset(
        (page_number - 1) * PAGE_SIZE).limit(PAGE_SIZE + 1)).all()
    return render_template("pedidos_finalizados.html", registros=rows[:PAGE_SIZE],
        data=chosen, pagina=page_number, mais=len(rows) > PAGE_SIZE,
        anterior=url_for("order_history.page", data=chosen, todas="1" if all_dates else None, pagina=page_number - 1),
        proxima=url_for("order_history.page", data=chosen, todas="1" if all_dates else None, pagina=page_number + 1))
