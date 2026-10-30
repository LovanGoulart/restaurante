"""Tabelas aditivas; cada restaurante usa sua própria base SQLite."""

from models import db, now


class ConfiguracoesFiscais(db.Model):
    __tablename__ = "configuracoes_fiscais"
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(120), nullable=False)
    cnpj = db.Column(db.String(14), nullable=False)
    inscricao_estadual = db.Column(db.String(30), nullable=False)
    inscricao_municipal = db.Column(db.String(30), nullable=False, default="")
    regime_tributario = db.Column(db.String(1), nullable=False)
    ambiente = db.Column(db.String(20), nullable=False, default="homologacao")
    empresa_api_id = db.Column(db.String(40), nullable=False)
    token_cifrado = db.Column(db.Text, nullable=False)
    # Token administrativo da Focus: não é uma segunda senha de emissão.
    master_cifrado = db.Column(db.Text, nullable=False, default="")
    certificado_cifrado = db.Column(db.Text, nullable=False, default="")
    certificado_senha_cifrada = db.Column(db.Text, nullable=False, default="")
    certificado_validade = db.Column(db.DateTime)
    parametros = db.Column(db.JSON, nullable=False)
    emitir_automaticamente = db.Column(db.Boolean, nullable=False, default=False)
    atualizado = db.Column(db.DateTime, nullable=False, default=now)
    __table_args__ = (db.CheckConstraint("id = 1"),)


class RegraFiscal(db.Model):
    __tablename__ = "regra_fiscal"
    id = db.Column(db.Integer, primary_key=True)
    # Item não tem produto_id: a regra é ligada explicitamente ao nome gravado.
    nome_item = db.Column(db.String(120), nullable=False, unique=True)
    campos = db.Column(db.JSON, nullable=False)


class FiscalSequencia(db.Model):
    __tablename__ = "fiscal_sequencia"
    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(14), nullable=False)
    ambiente = db.Column(db.String(20), nullable=False)
    serie = db.Column(db.Integer, nullable=False)
    proximo_numero = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.UniqueConstraint("cnpj", "ambiente", "serie"),
        db.CheckConstraint("proximo_numero > 0"),
    )


class NotaFiscal(db.Model):
    __tablename__ = "nota_fiscal"
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    ambiente = db.Column(db.String(20), nullable=False)
    referencia = db.Column(db.String(80), nullable=False, unique=True)
    status = db.Column(db.String(30), nullable=False, default="pendente", index=True)
    snapshot = db.Column(db.JSON, nullable=False)
    token_cifrado = db.Column(db.Text, nullable=False)
    destinatario_cifrado = db.Column(db.Text, nullable=False, default="")
    payload = db.Column(db.JSON)
    numero = db.Column(db.Integer)
    serie = db.Column(db.Integer)
    chave_acesso = db.Column(db.String(44))
    danfe_url = db.Column(db.Text)
    xml_url = db.Column(db.Text)
    codigo_sefaz = db.Column(db.String(10))
    mensagem = db.Column(db.String(1500), nullable=False, default="")
    enviado_em = db.Column(db.DateTime)
    criado = db.Column(db.DateTime, nullable=False, default=now)
    atualizado = db.Column(db.DateTime, nullable=False, default=now)
    proxima_consulta = db.Column(db.DateTime, nullable=False, default=now)
    trava_ate = db.Column(db.DateTime)
    trava_id = db.Column(db.String(40))
    __table_args__ = (
        db.UniqueConstraint("pedido_id", "ambiente"),
        db.UniqueConstraint("ambiente", "serie", "numero"),
    )
