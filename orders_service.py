from flask import abort
from models import db, Produto, Item


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
        pedido.itens.append(
            Item(
                nome=prod.nome,
                preco=prod.preco,
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
                nome=i.nome,
                quantidade=i.quantidade,
                preco=i.preco,
                observacao=i.observacao,
                etapa=i.etapa,
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
