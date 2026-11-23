"""Tabelas aditivas de fidelidade; nenhuma coluna dos registros antigos é alterada."""
from models import db, now


class FidelidadeConfig(db.Model):
    __tablename__ = "fidelidade_config"
    id = db.Column(db.Integer, primary_key=True)
    ativo = db.Column(db.Boolean, nullable=False, default=False)
    valor_base = db.Column(db.Integer, nullable=False, default=2000)
    pontos_base = db.Column(db.Integer, nullable=False, default=3)


class FidelidadeRecompensa(db.Model):
    __tablename__ = "fidelidade_recompensa"
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    produto = db.relationship("Produto")
    pontos = db.Column(db.Integer, nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    descricao = db.Column(db.String(500), nullable=False, default="")
    __table_args__ = (db.CheckConstraint("pontos > 0"),)


class FidelidadePedido(db.Model):
    __tablename__ = "fidelidade_pedido"
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False, index=True)
    valor_produtos = db.Column(db.Integer, nullable=False, default=0)
    valor_base = db.Column(db.Integer, nullable=False, default=0)
    pontos_base = db.Column(db.Integer, nullable=False, default=0)
    pontos_previstos = db.Column(db.Integer, nullable=False, default=0)
    recompensa_id = db.Column(db.Integer, db.ForeignKey("fidelidade_recompensa.id"))
    pontos_resgatados = db.Column(db.Integer, nullable=False, default=0)
    pedido = db.relationship("Pedido")
    cliente = db.relationship("Cliente")


class FidelidadeMovimento(db.Model):
    __tablename__ = "fidelidade_movimento"
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False, index=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    pontos = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.String(250), nullable=False)
    criado = db.Column(db.DateTime, nullable=False, default=now)
    __table_args__ = (db.UniqueConstraint("pedido_id", "tipo", name="uq_fidelidade_pedido_tipo"),)
