-- SQLite: tabelas novas. Prefira python fiscal_cli.py migrar para gerar backup automaticamente.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS configuracoes_fiscais (
	id INTEGER NOT NULL, 
	razao_social VARCHAR(120) NOT NULL, 
	cnpj VARCHAR(14) NOT NULL, 
	inscricao_estadual VARCHAR(30) NOT NULL, 
	inscricao_municipal VARCHAR(30) NOT NULL, 
	regime_tributario VARCHAR(1) NOT NULL, 
	ambiente VARCHAR(20) NOT NULL, 
	empresa_api_id VARCHAR(40) NOT NULL, 
	token_cifrado TEXT NOT NULL, 
	master_cifrado TEXT NOT NULL, 
	certificado_cifrado TEXT NOT NULL, 
	certificado_senha_cifrada TEXT NOT NULL, 
	certificado_validade DATETIME, 
	parametros JSON NOT NULL, 
	emitir_automaticamente BOOLEAN NOT NULL, 
	atualizado DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (id = 1)
);

CREATE TABLE IF NOT EXISTS regra_fiscal (
	id INTEGER NOT NULL, 
	nome_item VARCHAR(120) NOT NULL, 
	campos JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nome_item)
);

CREATE TABLE IF NOT EXISTS fiscal_sequencia (
	id INTEGER NOT NULL, 
	cnpj VARCHAR(14) NOT NULL, 
	ambiente VARCHAR(20) NOT NULL, 
	serie INTEGER NOT NULL, 
	proximo_numero INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (cnpj, ambiente, serie), 
	CHECK (proximo_numero > 0)
);

CREATE TABLE IF NOT EXISTS nota_fiscal (
	id INTEGER NOT NULL, 
	pedido_id INTEGER NOT NULL, 
	ambiente VARCHAR(20) NOT NULL, 
	referencia VARCHAR(80) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	snapshot JSON NOT NULL, 
	token_cifrado TEXT NOT NULL, 
	destinatario_cifrado TEXT NOT NULL, 
	payload JSON, 
	numero INTEGER, 
	serie INTEGER, 
	chave_acesso VARCHAR(44), 
	danfe_url TEXT, 
	xml_url TEXT, 
	codigo_sefaz VARCHAR(10), 
	mensagem VARCHAR(1500) NOT NULL, 
	enviado_em DATETIME, 
	criado DATETIME NOT NULL, 
	atualizado DATETIME NOT NULL, 
	proxima_consulta DATETIME NOT NULL, 
	trava_ate DATETIME, 
	trava_id VARCHAR(40), 
	PRIMARY KEY (id), 
	UNIQUE (pedido_id, ambiente), 
	UNIQUE (ambiente, serie, numero), 
	FOREIGN KEY(pedido_id) REFERENCES pedido (id), 
	UNIQUE (referencia)
);

CREATE INDEX IF NOT EXISTS ix_nota_fiscal_status ON nota_fiscal (status);

COMMIT;
