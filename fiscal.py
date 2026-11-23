"""Painel e endpoints fiscais exclusivos do administrador, sob liberação de senha."""

import base64
import hashlib
import json
import re
import secrets
import time
from functools import wraps
from datetime import datetime, timezone
from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    jsonify,
    render_template,
    request,
    session,
)
from cryptography.hazmat.primitives.serialization import pkcs12
from models import db, Produto, Item, Pedido, Movimento, now
from fiscal_models import ConfiguracoesFiscais, FiscalSequencia, RegraFiscal, NotaFiscal
from fiscal_service import (
    encrypt,
    decrypt,
    rate,
    valid_cnpj,
    validate_rule,
    enqueue,
    public_config,
)
from fiscal_provider import call, nfce_path, ProviderError
from customer_security import throttle, cpf_valido

bp = Blueprint("fiscal", __name__)


def admin(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if not g.user:
            abort(401)
        if g.user.perfil != "admin":
            abort(403)
        return fn(*args, **kwargs)

    return wrap


@bp.errorhandler(ValueError)
def invalid(exc):
    return jsonify(error=str(exc)), 400


@bp.errorhandler(ProviderError)
def provider_failed(exc):
    return jsonify(error=str(exc)), 502


def integer(value, low, high, label):
    if not re.fullmatch(r"\d{1,9}", str(value or "")) or not low <= int(value) <= high:
        raise ValueError(f"{label}: informe um número entre {low} e {high}.")
    return int(value)


def credentials(form):
    current = db.session.get(ConfiguracoesFiscais, 1)
    env = form.get("ambiente", "homologacao")
    cnpj = re.sub(r"[.\-/\s]", "", form.get("cnpj", "")).upper()
    company_id = form.get("empresa_api_id", "").strip()
    if env not in {"homologacao", "producao"} or not valid_cnpj(cnpj):
        raise ValueError(
            "Informe o ambiente e um CNPJ com dígitos verificadores válidos."
        )
    if not re.fullmatch(r"\d{1,30}", company_id):
        raise ValueError("Informe o ID numérico da empresa cadastrada na Focus NFe.")
    token = form.get("token", "").strip()
    master = form.get("master", "").strip()
    same = (
        current
        and current.ambiente == env
        and current.cnpj == cnpj
        and current.empresa_api_id == company_id
    )
    if not token and same:
        token = decrypt(current.token_cifrado)
    if not master and current:
        master = decrypt(current.master_cifrado)
    if (
        not token
        or not master
        or len(token) > 512
        or len(master) > 512
        or ":" in token
        or ":" in master
    ):
        raise ValueError(
            "Informe o token de emissão do ambiente e o token administrativo (Master). Mudou CNPJ, ID ou ambiente? Informe novamente o token de emissão."
        )
    return env, cnpj, company_id, token, master


def credential_hash(values):
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


@bp.get("/fiscal")
@admin
def panel():
    from sqlalchemy import inspect

    if not inspect(db.engine).has_table("configuracoes_fiscais"):
        return render_template("fiscal.html", missing=True), 503
    config = db.session.get(ConfiguracoesFiscais, 1)
    rules = db.session.scalars(
        db.select(RegraFiscal).order_by(RegraFiscal.nome_item)
    ).all()
    names = sorted(
        set(db.session.scalars(db.select(Produto.nome)))
        | set(db.session.scalars(db.select(Item.nome)))
    )
    page = max(1, request.args.get("pagina", 1, type=int))
    notes = db.session.scalars(
        db.select(NotaFiscal)
        .order_by(NotaFiscal.id.desc())
        .limit(20)
        .offset((page - 1) * 20)
    ).all()
    params = (
        config.parametros
        if config
        else {"serie": 1, "aliquota_icms": "", "pix_codigo": "20"}
    )
    seq = (
        db.session.scalar(
            db.select(FiscalSequencia).where(
                FiscalSequencia.cnpj == config.cnpj,
                FiscalSequencia.ambiente == config.ambiente,
                FiscalSequencia.serie == params["serie"],
            )
        )
        if config
        else None
    )
    return render_template(
        "fiscal.html",
        missing=False,
        config=config,
        params=params,
        next_number=seq.proximo_numero if seq else 1,
        rules=rules,
        names=names,
        notes=notes,
        page=page,
        production_enabled=current_app.config.get("FISCAL_PRODUCTION_ENABLED", False),
    )


@bp.post("/fiscal/testar")
@admin
def test_connection():
    throttle("fiscal-test:" + str(g.user.id), 10, 300)
    values = credentials(request.form)
    env, cnpj, company_id, token, master = values
    # Empresas é endpoint administrativo de produção, inclusive para emitente de teste.
    code, data = call("producao", master, "GET", "/v2/empresas/" + company_id)
    if (
        code != 200
        or re.sub(r"[.\-/\s]", "", str(data.get("cnpj", ""))).upper() != cnpj
    ):
        raise ValueError(
            "Não foi possível validar o CNPJ/ID com o token Master. Confira os dados da empresa no painel Focus."
        )
    provider_token = data.get("token_" + env)
    if not provider_token or provider_token != token:
        raise ValueError(
            "O token de emissão não corresponde à empresa e ao ambiente selecionados."
        )
    code, probe = call(
        env,
        token,
        "GET",
        nfce_path("teste-conexao-" + secrets.token_hex(16)),
    )
    if not (
        code == 404 and probe.get("codigo") in {"nao_encontrado", "nfce_nao_encontrada"}
    ):
        raise ValueError(
            "Token de emissão não validado. O teste exige retorno autenticado de referência inexistente; confira permissões com a Focus."
        )
    session["fiscal_test"] = {"hash": credential_hash(values), "at": time.time()}
    return jsonify(
        ok=True,
        message="Conexão validada sem emitir nota. CNPJ, ID, token do ambiente e autenticação conferidos.",
    )


@bp.post("/fiscal/configurar")
@admin
def configure():
    values = credentials(request.form)
    tested = session.get("fiscal_test", {})
    if (
        tested.get("hash") != credential_hash(values)
        or tested.get("at", 0) < time.time() - 600
    ):
        raise ValueError(
            "Clique em Testar conexão antes de salvar. O teste vale por dez minutos para estas credenciais."
        )
    env, cnpj, company_id, token, master = values
    name = request.form.get("razao_social", "").strip()
    ie = request.form.get("inscricao_estadual", "").strip()
    im = request.form.get("inscricao_municipal", "").strip()
    crt = request.form.get("regime_tributario", "")
    if (
        not 2 <= len(name) <= 120
        or not 1 <= len(ie) <= 30
        or len(im) > 30
        or crt not in {"1", "2", "3", "4"}
    ):
        raise ValueError(
            "Preencha razão social, inscrição estadual e regime tributário."
        )
    series = integer(request.form.get("serie"), 1, 999, "Série")
    next_number = integer(
        request.form.get("proximo_numero"), 1, 999999999, "Próximo número"
    )
    aliquota = request.form.get("aliquota_icms", "").strip()
    if aliquota:
        aliquota = str(rate(aliquota))
    uf = request.form.get("uf_emitente", "").strip().upper()
    if (
        uf
        not in "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
    ):
        raise ValueError("Informe a UF do estabelecimento.")
    pix = request.form.get("pix_codigo", "20")
    if pix not in {"17", "20"}:
        raise ValueError(
            "Escolha Pix estático ou dinâmico conforme o recebimento real."
        )
    auto = request.form.get("emitir_automaticamente") == "on"
    if env == "producao" and request.form.get("confirmar_producao") != "on":
        raise ValueError(
            "Confirme que a empresa está credenciada e a tributação foi validada para produção."
        )
    config = db.session.get(ConfiguracoesFiscais, 1)
    # Não permitir trocar emitente sob documentos já emitidos no mesmo tenant.
    if (
        config
        and config.cnpj != cnpj
        and db.session.scalar(db.select(NotaFiscal.id).limit(1))
    ):
        raise ValueError(
            "Este restaurante já possui histórico fiscal. Cadastre outro estabelecimento para trocar o CNPJ."
        )
    upload = request.files.get("certificado")
    cert = None
    if upload and upload.filename:
        if not upload.filename.lower().endswith((".pfx", ".p12")):
            raise ValueError("Envie um certificado A1 .pfx ou .p12.")
        raw = upload.read(1024 * 1024 + 1)
        password = request.form.get("senha_certificado", "")
        if len(raw) > 1024 * 1024 or not raw:
            raise ValueError("O certificado deve ter no máximo 1 MB.")
        try:
            key, certificate, _ = pkcs12.load_key_and_certificates(
                raw, password.encode() or None
            )
            if not key or not certificate:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(
                "Arquivo PFX ou senha inválidos; o certificado deve conter a chave privada."
            ) from None
        at = datetime.now(timezone.utc)
        if not certificate.not_valid_before_utc <= at < certificate.not_valid_after_utc:
            raise ValueError("O certificado está fora da validade.")
        # CNPJ e autenticidade ICP-Brasil são validados pelo provedor no envio.
        cert = (
            base64.b64encode(raw).decode(),
            password,
            certificate.not_valid_after_utc.replace(tzinfo=None),
        )
    # Cifrar antes de adicionar a primeira configuração (a chave só pode ser criada antes dela).
    cipher_token, cipher_master = encrypt(token), encrypt(master)
    cipher_cert = (encrypt(cert[0]), encrypt(cert[1]), cert[2]) if cert else None
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))
    config = db.session.get(ConfiguracoesFiscais, 1)
    seq = db.session.scalar(
        db.select(FiscalSequencia).where(
            FiscalSequencia.cnpj == cnpj,
            FiscalSequencia.ambiente == env,
            FiscalSequencia.serie == series,
        )
    )
    if seq and next_number < seq.proximo_numero:
        raise ValueError(
            "A numeração avançou ou foi reservada. Recarregue a página; não reduza o próximo número."
        )
    if not seq:
        seq = FiscalSequencia(cnpj=cnpj, ambiente=env, serie=series)
        db.session.add(seq)
    seq.proximo_numero = next_number
    if not config:
        config = ConfiguracoesFiscais(id=1)
        db.session.add(config)
    config.razao_social, config.cnpj = name, cnpj
    config.inscricao_estadual, config.inscricao_municipal = ie, im
    config.regime_tributario, config.ambiente, config.empresa_api_id = (
        crt,
        env,
        company_id,
    )
    config.token_cifrado, config.master_cifrado = cipher_token, cipher_master
    config.parametros = {
        "serie": series,
        "aliquota_icms": aliquota,
        "pix_codigo": pix,
        "uf": uf,
    }
    config.emitir_automaticamente, config.atualizado = auto, now()
    if cipher_cert:
        (
            config.certificado_cifrado,
            config.certificado_senha_cifrada,
            config.certificado_validade,
        ) = cipher_cert
    db.session.commit()
    return jsonify(
        ok=True,
        message="Configuração salva. O certificado local deve ser enviado à Focus pelo botão específico.",
    )


@bp.post("/fiscal/certificado/enviar")
@admin
def send_certificate():
    throttle("fiscal-certificate:" + str(g.user.id), 5, 300)
    config = db.session.get(ConfiguracoesFiscais, 1)
    if not config or not config.certificado_cifrado:
        raise ValueError("Salve primeiro o certificado e a configuração.")
    master = decrypt(config.master_cifrado)
    code, company = call(
        "producao", master, "GET", "/v2/empresas/" + config.empresa_api_id
    )
    if (
        code != 200
        or re.sub(r"[.\-/\s]", "", str(company.get("cnpj", ""))).upper() != config.cnpj
    ):
        raise ValueError(
            "O ID da empresa não corresponde ao CNPJ. Certificado não enviado."
        )
    # Somente arquivo e senha; não mudar cadastro/CSC/numeração já definidos na Focus.
    code, _ = call(
        "producao",
        master,
        "PUT",
        "/v2/empresas/" + config.empresa_api_id,
        {
            "arquivo_certificado_base64": decrypt(config.certificado_cifrado),
            "senha_certificado": decrypt(config.certificado_senha_cifrada),
            "certificado_especifico": True,
        },
    )
    if not 200 <= code < 300:
        raise ValueError(
            "A Focus não confirmou o certificado. Verifique senha, CNPJ e cadeia ICP-Brasil no painel do provedor."
        )
    return jsonify(
        ok=True,
        message="Certificado enviado à Focus. Confira CSC e credenciamento no painel do provedor.",
    )


@bp.post("/fiscal/regras")
@admin
def save_rule():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        raise ValueError("Envie um objeto JSON com nome_item e campos.")
    name = str(data.get("nome_item", "")).strip()
    if not name or len(name) > 120:
        raise ValueError("Informe o nome exato do item.")
    fields = validate_rule(data.get("campos"))
    rule = db.session.scalar(
        db.select(RegraFiscal).where(RegraFiscal.nome_item == name)
    )
    if not rule:
        rule = RegraFiscal(nome_item=name)
        db.session.add(rule)
    rule.campos = fields
    db.session.commit()
    return jsonify(ok=True, message="Tributação do item salva.")


@bp.post("/fiscal/pedidos/<int:id>/emitir")
@admin
def emit_paid_order(id):
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))
    order = db.get_or_404(Pedido, id)
    payment = db.session.scalar(
        db.select(Movimento).where(
            Movimento.pedido_id == id, Movimento.tipo == "recebimento"
        )
    )
    if not order.pago or not payment or payment.valor != order.total:
        raise ValueError("A comanda precisa estar paga e conciliada com o caixa.")
    note = enqueue(order, payment.forma, force=True)
    if not note:
        raise ValueError("Salve a configuração fiscal primeiro.")
    db.session.commit()
    return jsonify(
        ok=True,
        id=note.id,
        status=note.status,
        message="Nota incluída na fila fiscal. O processador fará a emissão.",
    )


@bp.post("/fiscal/notas/<int:id>/consultar")
@admin
def consult_note(id):
    note = db.get_or_404(NotaFiscal, id)
    # Sem rede no navegador; consulta pendente executada pelo mesmo worker.
    if note.status == "processando":
        note.proxima_consulta = now()
        db.session.commit()
    return jsonify(
        ok=True,
        status=note.status,
        message="Consulta agendada. Recarregue a lista após o processamento.",
    )


@bp.post("/fiscal/notas/<int:id>/corrigir")
@admin
def fix_unsent(id):
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))
    note = db.get_or_404(NotaFiscal, id)
    if note.enviado_em or note.status != "erro_configuracao":
        raise ValueError(
            "Somente notas ainda não enviadas podem ser preparadas novamente."
        )
    config = db.session.get(ConfiguracoesFiscais, 1)
    if (
        not config
        or config.ambiente != note.ambiente
        or config.cnpj != note.snapshot["empresa"]["cnpj"]
    ):
        raise ValueError(
            "Ambiente ou CNPJ mudou. Restaure a configuração da nota para corrigi-la."
        )
    rules = {r.nome_item: r.campos for r in db.session.scalars(db.select(RegraFiscal))}
    snap = json.loads(json.dumps(note.snapshot))
    snap["empresa"] = public_config(config)
    for item in snap["itens"]:
        item["regra"] = rules.get(item["nome"])
    note.snapshot, note.token_cifrado = snap, config.token_cifrado
    note.status, note.mensagem, note.proxima_consulta = "pendente", "", now()
    db.session.commit()
    return jsonify(
        ok=True,
        message="Dados fiscais atualizados. Valores originais da comanda preservados.",
    )


@bp.post("/fiscal/notas/<int:id>/destinatario")
@admin
def save_recipient(id):
    db.session.rollback()
    db.session.execute(db.text("BEGIN IMMEDIATE"))
    note = db.get_or_404(NotaFiscal, id)
    if (
        note.enviado_em
        or note.status not in {"pendente", "erro_configuracao"}
        or note.trava_ate
    ):
        raise ValueError(
            "O destinatário só pode ser alterado antes do envio e fora do processamento."
        )
    form = request.form
    cpf = form.get("cpf", "").strip()
    if not cpf_valido(cpf):
        raise ValueError("Informe um CPF com dígitos verificadores válidos.")
    recipient = {"cpf_destinatario": re.sub(r"\D", "", cpf)}
    for name, minimum, maximum in [
        ("nome", 2, 100),
        ("logradouro", 2, 120),
        ("numero", 1, 20),
        ("bairro", 2, 80),
        ("municipio", 2, 80),
    ]:
        value = form.get(name, "").strip()
        if not minimum <= len(value) <= maximum:
            raise ValueError("Confira o campo " + name + " do destinatário.")
        recipient[name + "_destinatario"] = value
    uf = form.get("uf", "").strip().upper()
    cep = re.sub(r"[.\-\s]", "", form.get("cep", ""))
    if uf not in "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split() or not re.fullmatch(
        r"\d{8}", cep
    ):
        raise ValueError("Informe UF e CEP válidos do destinatário.")
    recipient.update(uf_destinatario=uf, cep_destinatario=cep)
    # NFC-e desta versão é venda interna; não presumir entrega interestadual.
    config = db.session.get(ConfiguracoesFiscais, 1)
    if not config or uf != config.parametros.get("uf"):
        raise ValueError(
            "Esta versão emite vendas dentro da UF do estabelecimento. Confira a UF nos parâmetros fiscais."
        )
    note.destinatario_cifrado = encrypt(json.dumps(recipient))
    db.session.commit()
    return jsonify(
        ok=True,
        message="Destinatário salvo. Se a nota estiver com erro, use Preparar com os dados corrigidos.",
    )
