import json
import time
from datetime import datetime, timedelta, timezone
from app import app
from models import db, Notificacao, PushSubscription, PushDelivery, Usuario, Pedido
from notifications import push_config
from config import DATA


def process_pending(send=None):
    if send is None:
        from pywebpush import webpush

        send = webpush
    config = push_config()
    if not config:
        return 0
    ids = db.session.scalars(
        db.select(PushDelivery.id)
        .where(
            PushDelivery.estado == "pendente",
            PushDelivery.proxima <= datetime.now(timezone.utc),
        )
        .order_by(PushDelivery.id)
        .limit(30)
    ).all()
    count = 0
    for id in ids:
        (DATA / "push-worker.heartbeat").touch()
        task = db.session.get(PushDelivery, id)
        n = db.session.get(Notificacao, task.notificacao_id)
        sub = db.session.get(PushSubscription, task.subscription_id)
        u = db.session.get(Usuario, sub.usuario_id) if sub else None
        pedido = db.session.get(Pedido, n.pedido_id) if n and n.pedido_id else None
        stale = bool(
            n
            and pedido
            and (
                n.tipo == "pronto"
                and pedido.status != "pronto"
                or n.tipo == "novo"
                and pedido.status != "aberto"
                or n.tipo in ["saiu_entrega", "atribuida"]
                and pedido.status != "saiu_entrega"
            )
        )
        if (
            u
            and u.perfil == "entregador"
            and pedido
            and (not pedido.entrega or pedido.entrega.entregador_id != u.id)
        ):
            stale = True
        expired = bool(
            n
            and datetime.now(timezone.utc).replace(tzinfo=None)
            - n.criado.replace(tzinfo=None)
            > timedelta(minutes=15)
        )
        if (
            not n
            or not sub
            or not sub.ativo
            or not u
            or not u.ativo
            or u.id != n.usuario_id
            or n.lida
            or stale
            or expired
        ):
            task.estado = "cancelado"
            db.session.commit()
            continue
        payload = json.dumps(
            {
                "id": n.id,
                "title": n.titulo,
                "body": n.mensagem,
                "url": (
                    "/entregas"
                    if u.perfil == "entregador"
                    else "/meus-pedidos" if u.perfil == "cliente" else "/pedidos"
                ),
            },
            ensure_ascii=False,
        )
        subscription = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        # Libera a transação durante I/O de rede.
        db.session.remove()
        error = None
        try:
            send(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=config["private_key"],
                vapid_claims={"sub": config["subject"]},
                ttl=120,
                timeout=10,
            )
        except Exception as exc:
            error = exc
        task = db.session.get(PushDelivery, id)
        if not task:
            continue
        task.tentativas += 1
        if error is None:
            task.estado = "enviado"
            count += 1
        else:
            code = getattr(getattr(error, "response", None), "status_code", None)
            if code in [404, 410]:
                sub = db.session.get(PushSubscription, task.subscription_id)
                if sub:
                    sub.ativo = False
                task.estado = "expirado"
            elif task.tentativas >= 5:
                task.estado = "falhou"
            else:
                task.proxima = datetime.now(timezone.utc) + timedelta(
                    seconds=min(300, 15 * 2**task.tentativas)
                )
            # Não registrar endpoints, chaves ou conteúdo dos pedidos.
            print(
                f'Push #{id}: tentativa {task.tentativas}; HTTP {code or "indisponível"}',
                flush=True,
            )
        db.session.commit()
    return count


def run():
    print("Worker de notificações iniciado.", flush=True)
    while True:
        try:
            with app.app_context():
                (DATA / "push-worker.heartbeat").touch()
                process_pending()
        except Exception as exc:
            print("Worker aguardando recuperação: " + type(exc).__name__, flush=True)
        time.sleep(2)


if __name__ == "__main__":
    run()
