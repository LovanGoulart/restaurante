from flask import abort
from models import db, Produto, Item
from product_options import resolve_item


def add_items(pedido, itens):
    if not isinstance(itens, list) or not 1 <= len(itens) <= 100:
        abort(400, "Inclua ao menos um produto no pedido.")
    for item in itens:
        if (
            not isinstance(item, dict)
            or type(item.get("id")) is not int
            or type(item.get("quantidade")) is not int
            or not 1 <= item["quantidade"] <= 99
        ):
            abort(400, "Item ou quantidade inválida.")
        prod = db.session.get(Produto, item["id"])
        obs = item.get("observacao", "")
        if not isinstance(obs, str) or len(obs) > 300 or not prod or not prod.ativo:
            abort(400, "Produto indisponível ou observação inválida.")
        price, obs = resolve_item(prod, item)
        pedido.itens.append(
            Item(
                nome=prod.nome,
                preco=price,
                quantidade=item["quantidade"],
                observacao=obs.strip(),
            )
        )


def serialize_order(p, user):
    online = p.online
    guest = user.perfil == "visitante"
    if guest and not any(q.usuario_id == user.id for q in p.qr):
        abort(403)
    items = [i for i in p.itens if not guest or i.visitante_id == user.id]
    if user.perfil == "entregador" and (
        not online
        or online.modalidade != "entrega"
        or not p.entrega
        or p.entrega.entregador_id != user.id
    ):
        abort(403)
    result = dict(
        id=p.id,
        canal="online" if online else "salao",
        modalidade=online.modalidade if online else "salao",
        mesa=p.mesa if not online else "",
        comanda=p.mesa if not online else "",
        numero_mesa=p.numero_mesa if not online else "",
        pedido_qr=bool(p.qr),
        aguardando_comanda=bool(p.qr and not p.mesa),
        status=p.status,
        pago=p.pago,
        subtotal=sum(i.preco * i.quantidade for i in items) if guest else p.subtotal,
        taxa_entrega=online.taxa_entrega if online else 0,
        total=sum(i.preco * i.quantidade for i in items) if guest else p.total,
        garcom=(user.nome if guest else p.usuario.nome) if not online else "",
        cliente=online.destinatario if online else "",
        criado=p.criado.isoformat(),
        itens=[
            dict(
                id=i.id,
                nome=i.nome,
                quantidade=i.quantidade,
                preco=i.preco,
                observacao=i.observacao,
                etapa="entregue" if p.status == "entregue" else i.etapa,
            )
            for i in items
        ],
    )
    # Cozinha recebe somente nome/modalidade/itens; garçom não recebe pedidos online.
    if online and user.perfil in ["admin", "cliente", "entregador"]:
        result.update(
            forma_pagamento=online.forma_pagamento, troco_para=online.troco_para
        )
        if online.modalidade == "entrega":
            result["endereco"] = dict(
                endereco=online.endereco,
                bairro=online.bairro,
                numero=online.numero,
                referencia=online.referencia,
                telefone=online.telefone,
            )
    if user.perfil == "admin" and p.entrega:
        e = p.entrega
        result["entregador"] = dict(
            id=e.entregador_id,
            nome=e.entregador.nome,
            concluida=bool(e.entregue_em),
            forma_pagamento=e.forma_pagamento,
            valor_recebido=e.valor_recebido,
            acertado=bool(e.acertado_em),
        )
    return result


def checklist_status(pedido):
    """O status geral acompanha os itens que ainda faltam servir."""
    stages = [i.etapa for i in pedido.itens]
    if not stages:
        return pedido.status
    if all(stage == "entregue" for stage in stages):
        return "entregue"
    pending = [stage for stage in stages if stage != "entregue"]
    if all(stage == "pronto" for stage in pending):
        return "pronto"
    if any(stage in {"em_preparo", "pronto", "entregue"} for stage in stages):
        return "em_preparo"
    return "aberto"


def update_item_checklist(pedido, item, user, action, checked, expected):
    if user.perfil not in {"admin", "cozinha", "garcom"}:
        abort(403)
    if action not in {"pronto", "entregue"} or type(checked) is not bool:
        abort(400, "Marcação de item inválida.")
    if user.perfil == "cozinha" and action != "pronto":
        abort(403)
    if user.perfil == "garcom" and (pedido.online or action != "entregue"):
        abort(403)
    if action == "entregue" and pedido.online:
        abort(
            403,
            "Nos pedidos online, utilize a confirmação de retirada ou entrega do pedido.",
        )
    if pedido.status == "saiu_entrega" or (
        pedido.entrega and pedido.entrega.entregue_em
    ):
        abort(409, "Pedido já encaminhado ao entregador ou com entrega confirmada.")
    if pedido.status == "entregue" and pedido.pago:
        abort(409, "Comanda finalizada. O checklist não pode mais ser alterado.")
    if action == "entregue" and pedido.qr and not pedido.mesa:
        abort(
            409,
            "Defina a comanda e confira a mesa antes de registrar a entrega do item.",
        )
    if expected not in {"aberto", "em_preparo", "pronto", "entregue"}:
        abort(400, "Etapa anterior inválida. Reabra os detalhes do pedido.")
    # Compatibilidade com pedidos antigos entregues pelo botão geral.
    if pedido.status == "entregue":
        for row in pedido.itens:
            row.etapa = "entregue"
    current = item.etapa
    if current == "entregue" and action == "pronto":
        abort(409, "Este item já foi entregue; a cozinha não pode desfazer a entrega.")
    target = action if checked else "em_preparo" if action == "pronto" else "pronto"
    if current == target:
        return False
    if current != expected:
        abort(
            409, "Este item foi atualizado por outro usuário. Confira a marcação atual."
        )
    # Não é possível desmarcar uma etapa que nunca foi marcada.
    if not checked and current != action:
        abort(409, "O item mudou. Confira a marcação atual.")
    item.etapa = target
    pedido.status = checklist_status(pedido)
    return True
