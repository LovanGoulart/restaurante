from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc)


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(80), unique=True, nullable=False)
    senha = db.Column(db.String(256), nullable=False)
    perfil = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)


class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)


class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.String(500), default="")
    preco = db.Column(db.Integer, nullable=False)
    emoji = db.Column(db.String(10), default="🍽️")
    ativo = db.Column(db.Boolean, default=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categoria.id"), nullable=False)
    categoria = db.relationship(Categoria)


class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mesa = db.Column(db.String(40), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    usuario = db.relationship(Usuario)
    status = db.Column(db.String(20), default="aberto", nullable=False)
    pago = db.Column(db.Boolean, default=False, nullable=False)
    criado = db.Column(db.DateTime, default=now)
    itens = db.relationship("Item", cascade="all, delete-orphan")
    online = db.relationship("PedidoOnline", uselist=False, back_populates="pedido")
    entrega = db.relationship("Entrega", uselist=False, back_populates="pedido")

    @property
    def subtotal(self):
        return sum(i.preco * i.quantidade for i in self.itens)

    @property
    def total(self):
        return self.subtotal + (self.online.taxa_entrega if self.online else 0)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    preco = db.Column(db.Integer, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    observacao = db.Column(db.String(300), default="")


class Caixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aberto = db.Column(db.DateTime, default=now)
    fechado = db.Column(db.DateTime)
    inicial = db.Column(db.Integer, nullable=False)
    contado = db.Column(db.Integer)


class Movimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caixa_id = db.Column(db.Integer, db.ForeignKey("caixa.id"), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), unique=True)
    tipo = db.Column(db.String(20), nullable=False)
    forma = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.String(200), default="")
    criado = db.Column(db.DateTime, default=now)


class Notificacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False, index=True
    )
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"))
    titulo = db.Column(db.String(120), nullable=False)
    mensagem = db.Column(db.String(250), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    alerta = db.Column(db.Boolean, default=False, nullable=False)
    lida = db.Column(db.Boolean, default=False, nullable=False)
    criado = db.Column(db.DateTime, default=now, nullable=False)


class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False, index=True
    )
    endpoint = db.Column(db.String(2048), unique=True, nullable=False)
    p256dh = db.Column(db.String(160), nullable=False)
    auth = db.Column(db.String(80), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)


class PushDelivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notificacao_id = db.Column(
        db.Integer, db.ForeignKey("notificacao.id"), nullable=False
    )
    subscription_id = db.Column(
        db.Integer, db.ForeignKey("push_subscription.id"), nullable=False
    )
    tentativas = db.Column(db.Integer, default=0, nullable=False)
    estado = db.Column(db.String(20), default="pendente", nullable=False, index=True)
    proxima = db.Column(db.DateTime, default=now, nullable=False)
    __table_args__ = (db.UniqueConstraint("notificacao_id", "subscription_id"),)


class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False, unique=True
    )
    usuario = db.relationship(Usuario)
    cpf_cifrado = db.Column(db.Text, nullable=False)
    cpf_hash = db.Column(db.String(64), nullable=False, unique=True)
    cpf_final = db.Column(db.String(2), nullable=False)
    nascimento = db.Column(db.Date, nullable=False)
    telefone = db.Column(db.String(25), default="")
    endereco = db.Column(db.String(160), default="")
    bairro = db.Column(db.String(100), default="")
    numero = db.Column(db.String(20), default="")
    referencia = db.Column(db.String(200), default="")


class Loja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, default="Restaurante Manager")
    taxa_entrega = db.Column(db.Integer, nullable=False, default=0)
    entrega_ativa = db.Column(db.Boolean, nullable=False, default=True)
    pedidos_ativos = db.Column(db.Boolean, nullable=False, default=True)


class PedidoOnline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(
        db.Integer, db.ForeignKey("pedido.id"), nullable=False, unique=True
    )
    pedido = db.relationship(Pedido, back_populates="online")
    cliente_id = db.Column(
        db.Integer, db.ForeignKey("cliente.id"), nullable=False, index=True
    )
    modalidade = db.Column(db.String(20), nullable=False)
    destinatario = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(25), default="")
    endereco = db.Column(db.String(160), default="")
    bairro = db.Column(db.String(100), default="")
    numero = db.Column(db.String(20), default="")
    referencia = db.Column(db.String(200), default="")
    forma_pagamento = db.Column(db.String(20), nullable=False)
    troco_para = db.Column(db.Integer)
    taxa_entrega = db.Column(db.Integer, nullable=False, default=0)


class EnvioPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    chave = db.Column(db.String(80), nullable=False)
    conteudo_hash = db.Column(db.String(64), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("usuario_id", "chave"),)


class TentativaAcesso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(64), nullable=False, index=True)
    criado = db.Column(db.DateTime, default=now, nullable=False, index=True)


class Entrega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(
        db.Integer, db.ForeignKey("pedido.id"), nullable=False, unique=True
    )
    pedido = db.relationship(Pedido, back_populates="entrega")
    entregador_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False, index=True
    )
    entregador = db.relationship(Usuario, foreign_keys=[entregador_id])
    atribuido_em = db.Column(db.DateTime, default=now, nullable=False)
    entregue_em = db.Column(db.DateTime, index=True)
    forma_pagamento = db.Column(db.String(20))
    valor_pedido = db.Column(db.Integer, default=0, nullable=False)
    valor_recebido = db.Column(db.Integer, default=0, nullable=False)
    pago_antecipado = db.Column(db.Boolean, default=False, nullable=False)
    acertado_em = db.Column(db.DateTime)
    acertado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    movimento_id = db.Column(db.Integer, db.ForeignKey("movimento.id"), unique=True)
