"""Fidelidade integrada aos pedidos online, pagamentos e isolamento do restaurante."""
import secrets
from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, url_for
from sqlalchemy.dialects.sqlite import insert
from models import db, Produto, Cliente, Pedido, Item, now
from loyalty_models import FidelidadeConfig, FidelidadeRecompensa, FidelidadePedido, FidelidadeMovimento
from customers import role, profile, store, money

bp = Blueprint("loyalty", __name__)


def config():
    return db.session.get(FidelidadeConfig, 1)


def enabled():
    cfg = config()
    return bool(cfg and cfg.ativo)


@bp.app_context_processor
def menu_context():
    return {"loyalty_enabled": enabled() if g.get("user") and g.user.perfil == "cliente" else False}


def balance(cliente_id):
    return db.session.scalar(db.select(db.func.coalesce(db.func.sum(FidelidadeMovimento.pontos), 0)).where(
        FidelidadeMovimento.cliente_id == cliente_id)) or 0


def capture_order(p):
    """Regra imutável na compra; não pontua pedidos anteriores à implementação."""
    cfg = config()
    if not cfg or not cfg.ativo or not p.online or p.usuario.perfil != "cliente":
        return
    db.session.add(FidelidadePedido(
        pedido_id=p.id, cliente_id=p.online.cliente_id, valor_produtos=p.subtotal,
        valor_base=cfg.valor_base, pontos_base=cfg.pontos_base,
        pontos_previstos=(p.subtotal // cfg.valor_base) * cfg.pontos_base))


def credit_completed(p):
    """Chamado na mesma transação de pagamento/entrega. UNIQUE evita duplicação."""
    if not p.pago or p.status != "entregue" or not p.online:
        return
    row = db.session.get(FidelidadePedido, p.id)
    if not row or row.recompensa_id or row.pontos_previstos <= 0:
        return
    db.session.execute(insert(FidelidadeMovimento).values(
        cliente_id=row.cliente_id, pedido_id=p.id, tipo="ganho",
        pontos=row.pontos_previstos, descricao="Pontos por compra online concluída",
        criado=now()).on_conflict_do_nothing(index_elements=["pedido_id", "tipo"]))


def reward_item(p, d, c):
    """Executado dentro do BEGIN IMMEDIATE já usado pelo checkout online."""
    if not enabled():
        abort(403, "O programa de fidelidade está desabilitado.")
    rid = d.get("resgate_id")
    if type(rid) is not int:
        abort(400, "Recompensa inválida.")
    reward = db.session.get(FidelidadeRecompensa, rid)
    if not reward or not reward.ativo or not reward.produto.ativo or reward.produto.excluido:
        abort(409, "Este produto não está mais disponível para resgate.")
    if type(d.get("pontos_previstos")) is not int or d["pontos_previstos"] != reward.pontos:
        abort(409, "O custo em pontos mudou. Atualize a página antes de confirmar.")
    if d.get("itens"):
        abort(400, "O resgate deve ser confirmado em um pedido separado.")
    if balance(c.id) < reward.pontos:
        abort(409, "Pontos insuficientes para este resgate.")
    p.itens.append(Item(
        nome=reward.produto.nome, preco=0, quantidade=1,
        observacao=f"Fidelidade: {reward.pontos} pontos. " + reward.descricao))
    return reward


def record_redemption(p, reward, c):
    db.session.add(FidelidadePedido(
        pedido_id=p.id, cliente_id=c.id, recompensa_id=reward.id,
        pontos_resgatados=reward.pontos, pontos_previstos=0))
    db.session.add(FidelidadeMovimento(
        cliente_id=c.id, pedido_id=p.id, tipo="resgate", pontos=-reward.pontos,
        descricao=("Resgate: " + reward.produto.nome)[:250]))
    # Sem cobrança e sem movimento fictício no caixa quando não há taxa.
    if p.total == 0:
        p.pago = True


def rewards():
    return db.session.scalars(db.select(FidelidadeRecompensa).join(Produto).where(
        FidelidadeRecompensa.ativo.is_(True), Produto.ativo.is_(True),
        Produto.excluido.is_(False)).order_by(FidelidadeRecompensa.pontos, Produto.nome)).all()


def history(cid):
    return db.session.scalars(db.select(FidelidadeMovimento).where(
        FidelidadeMovimento.cliente_id == cid).order_by(FidelidadeMovimento.id.desc()).limit(100)).all()


@bp.get("/fidelidade")
@role("cliente")
def page():
    if not enabled():
        abort(403, "O programa de fidelidade está desabilitado.")
    c = profile()
    return render_template("fidelidade.html", cfg=config(), saldo=balance(c.id),
                           recompensas=rewards(), historico=history(c.id))


@bp.get("/api/fidelidade")
@role("cliente")
def state():
    if not enabled():
        abort(403, "O programa de fidelidade está desabilitado.")
    c = profile()
    return jsonify(saldo=balance(c.id), historico=[
        dict(pontos=m.pontos, descricao=m.descricao, pedido=m.pedido_id,
             criado=m.criado.isoformat() + "Z") for m in history(c.id)])


@bp.get("/fidelidade/resgatar/<int:id>")
@role("cliente")
def checkout(id):
    if not enabled():
        abort(403, "O programa de fidelidade está desabilitado.")
    c = profile()
    reward = next((r for r in rewards() if r.id == id), None)
    if not reward:
        abort(404)
    if balance(c.id) < reward.pontos:
        abort(409, "Pontos insuficientes para este resgate.")
    return render_template("fidelidade_resgate.html", recompensa=reward,
                           cliente=c, loja=store(), chave=secrets.token_hex(24))


def integer(value, label, maximum=1000000):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError(f"Informe um número inteiro positivo em {label}.")
    value = int(value)
    if not 1 <= value <= maximum:
        raise ValueError(f"{label}: use um valor entre 1 e {maximum}.")
    return value


@bp.route("/fidelidade-admin", methods=["GET", "POST"])
@role("admin")
def admin():
    error = None
    if request.method == "POST":
        db.session.rollback()
        db.session.execute(db.text("BEGIN IMMEDIATE"))
        try:
            action = request.form.get("acao")
            if action == "config":
                value = money(request.form.get("valor_base", ""))
                if value < 1:
                    raise ValueError("O valor de referência deve ser maior que zero.")
                points = integer(request.form.get("pontos_base", ""), "Pontos")
                cfg = config() or FidelidadeConfig(id=1)
                cfg.ativo = request.form.get("ativo") == "on"
                cfg.valor_base, cfg.pontos_base = value, points
                db.session.add(cfg)
            elif action in {"recompensa", "excluir"}:
                rid = request.form.get("id")
                reward = db.get_or_404(FidelidadeRecompensa, integer(rid, "Recompensa")) if rid else FidelidadeRecompensa()
                if action == "excluir":
                    if not rid:
                        raise ValueError("Escolha uma recompensa.")
                    reward.ativo = False
                else:
                    pid = integer(request.form.get("produto_id", ""), "Produto")
                    prod = db.get_or_404(Produto, pid)
                    if prod.excluido or not prod.ativo:
                        raise ValueError("Selecione um produto ativo.")
                    reward.produto_id = pid
                    reward.pontos = integer(request.form.get("pontos", ""), "Pontos para resgate")
                    desc = request.form.get("descricao", "").strip()
                    if len(desc) > 500:
                        raise ValueError("A descrição deve ter no máximo 500 caracteres.")
                    reward.descricao = desc
                    reward.ativo = True
                db.session.add(reward)
            else:
                raise ValueError("Ação inválida.")
            db.session.commit()
            return redirect(url_for("loyalty.admin", salvo=1,
                aba="programa" if action == "config" else "produtos"))
        except ValueError as exc:
            db.session.rollback()
            error = str(exc)
    edit = db.session.get(FidelidadeRecompensa, request.args.get("editar", type=int)) if request.args.get("editar", type=int) else None
    cid = request.args.get("cliente", type=int)
    selected = db.session.get(Cliente, cid) if cid else None
    entries = history(selected.id) if selected else []
    redemptions = db.session.scalars(db.select(FidelidadePedido).where(
        FidelidadePedido.recompensa_id.is_not(None)).order_by(FidelidadePedido.pedido_id.desc()).limit(100)).all()
    return render_template("fidelidade_admin.html", cfg=config(), error=error, editar=edit,
        produtos=db.session.scalars(db.select(Produto).where(Produto.ativo.is_(True), Produto.excluido.is_(False)).order_by(Produto.nome)).all(),
        recompensas=db.session.scalars(db.select(FidelidadeRecompensa).where(FidelidadeRecompensa.ativo.is_(True))).all(),
        clientes=db.session.scalars(db.select(Cliente).order_by(Cliente.id.desc())).all(),
        selecionado=selected, saldo=balance(selected.id) if selected else 0,
        historico=entries, resgates=redemptions)


@bp.post("/fidelidade-admin/resgates/<int:id>/cancelar")
@role("admin")
def cancel(id):
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))
    row = db.get_or_404(FidelidadePedido, id)
    p = row.pedido
    if not row.recompensa_id:
        abort(400, "Este pedido não é um resgate.")
    if p.status == "cancelado":
        return redirect(url_for("loyalty.admin", aba="resgates"))
    if p.status != "aberto" or p.entrega or (p.pago and p.total > 0):
        abort(409, "Só é possível cancelar resgates aguardando preparo e sem taxa já recebida.")
    if any(i.etapa != "aberto" for i in p.itens):
        abort(409, "O preparo já foi iniciado.")
    p.status = "cancelado"
    db.session.add(FidelidadeMovimento(
        cliente_id=row.cliente_id, pedido_id=p.id, tipo="estorno",
        pontos=row.pontos_resgatados, descricao="Estorno de resgate cancelado antes do preparo"))
    from notifications import emit_order
    emit_order(p, "cancelado")
    db.session.commit()
    return redirect(url_for("loyalty.admin", salvo=1, aba="resgates"))
