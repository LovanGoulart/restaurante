"""Outbox fiscal: fechamento local atômico; emissão fora da transação do caixa."""

import json
import secrets
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from flask import current_app
from cryptography.fernet import Fernet, InvalidToken
from config import data_dir
from models import db, now
from fiscal_models import ConfiguracoesFiscais, RegraFiscal, FiscalSequencia, NotaFiscal
from fiscal_provider import call, nfce_path, safe_document_url, ProviderError


def cipher():
    path = data_dir() / "fiscal-data.key"
    if not path.exists():
        if db.session.scalar(
            db.select(ConfiguracoesFiscais.id).limit(1)
        ) or db.session.scalar(db.select(NotaFiscal.id).limit(1)):
            raise ValueError(
                "Restaure fiscal-data.key do backup antes de usar as credenciais."
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # mode 0600 desde a criação, inclusive antes da primeira escrita.
            import os

            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(Fernet.generate_key())
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            pass
    return Fernet(path.read_bytes().strip())


def encrypt(value):
    return cipher().encrypt(value.encode()).decode() if value else ""


def decrypt(value):
    try:
        return cipher().decrypt(value.encode()).decode() if value else ""
    except (InvalidToken, OSError, ValueError):
        raise ValueError(
            "Credencial fiscal indisponível. Confira a chave fiscal do restaurante."
        ) from None


def amount(cents):
    return format(Decimal(cents) / 100, ".2f")


def rate(value):
    try:
        result = Decimal(str(value).replace(",", "."))
        if (
            not result.is_finite()
            or result < 0
            or result > 100
            or result.as_tuple().exponent < -4
        ):
            raise ValueError()
        return result
    except (InvalidOperation, ValueError):
        raise ValueError(
            "Informe uma alíquota entre 0 e 100, com até quatro casas decimais."
        ) from None


def valid_cnpj(value):
    if not re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", value) or len(set(value)) == 1:
        return False
    for size, weights in [
        (12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
        (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
    ]:
        rem = sum((ord(d) - 48) * w for d, w in zip(value[:size], weights)) % 11
        if int(value[size]) != (0 if rem < 2 else 11 - rem):
            return False
    return True


RULE_FIELDS = {
    "codigo_ncm",
    "cest",
    "cfop",
    "unidade",
    "icms_origem",
    "icms_situacao_tributaria",
    "icms_aliquota",
    "pis_situacao_tributaria",
    "pis_aliquota_porcentual",
    "cofins_situacao_tributaria",
    "cofins_aliquota_porcentual",
}


def validate_rule(rule):
    if (
        not isinstance(rule, dict)
        or set(rule) - RULE_FIELDS
        or any(not isinstance(value, str) for value in rule.values())
    ):
        raise ValueError("Campos fiscais do item inválidos.")
    for key, pattern in [
        ("codigo_ncm", r"\d{8}"),
        ("cfop", r"5\d{3}"),
        ("icms_origem", r"[0-8]"),
        ("icms_situacao_tributaria", r"102|500|00|40|41|60"),
        ("pis_situacao_tributaria", r"01|02|04|05|06|07|08|09"),
        ("cofins_situacao_tributaria", r"01|02|04|05|06|07|08|09"),
    ]:
        if not re.fullmatch(pattern, str(rule.get(key, ""))):
            raise ValueError(
                f"Confira {key}: campo obrigatório ou situação ainda não suportada."
            )
    if not re.fullmatch(r"[A-Za-z]{1,6}", rule.get("unidade", "")):
        raise ValueError("Informe a unidade comercial, por exemplo UN.")
    if rule.get("cest") and not re.fullmatch(r"\d{7}", rule["cest"]):
        raise ValueError("CEST deve ter sete dígitos.")
    for key in [
        "icms_aliquota",
        "pis_aliquota_porcentual",
        "cofins_aliquota_porcentual",
    ]:
        if str(rule.get(key, "")).strip():
            rate(rule[key])
    for prefix in ["pis", "cofins"]:
        if (
            rule[prefix + "_situacao_tributaria"] in {"01", "02"}
            and not str(rule.get(prefix + "_aliquota_porcentual", "")).strip()
        ):
            raise ValueError(f"Informe a alíquota de {prefix.upper()}.")
    return rule


def public_config(config):
    return {
        "cnpj": config.cnpj,
        "razao_social": config.razao_social,
        "inscricao_estadual": config.inscricao_estadual,
        "regime_tributario": config.regime_tributario,
        "parametros": dict(config.parametros),
    }


def enqueue(pedido, forma, force=False):
    """Chamado DENTRO da transação de recebimento. Sem rede nem commit próprio."""
    # Compatibilidade antes de instalar as tabelas: módulo desativado por padrão.
    from sqlalchemy import inspect

    if not inspect(db.session.connection()).has_table("configuracoes_fiscais"):
        return None
    config = db.session.get(ConfiguracoesFiscais, 1)
    if not config or (not force and not config.emitir_automaticamente):
        return None
    existing = db.session.scalar(
        db.select(NotaFiscal).where(
            NotaFiscal.pedido_id == pedido.id, NotaFiscal.ambiente == config.ambiente
        )
    )
    if existing:
        return existing
    rules = {r.nome_item: r.campos for r in db.session.scalars(db.select(RegraFiscal))}
    note = NotaFiscal(
        pedido_id=pedido.id,
        ambiente=config.ambiente,
        referencia="rm-" + secrets.token_hex(16),
        status="pendente",
        token_cifrado=config.token_cifrado,
        snapshot={
            "empresa": public_config(config),
            "forma": forma,
            "total": pedido.total,
            "frete": pedido.online.taxa_entrega if pedido.online else 0,
            "delivery": bool(pedido.online and pedido.online.modalidade == "entrega"),
            "itens": [
                {
                    "id": i.id,
                    "nome": i.nome,
                    "preco": i.preco,
                    "quantidade": i.quantidade,
                    "regra": rules.get(i.nome),
                }
                for i in pedido.itens
            ],
        },
    )
    db.session.add(note)
    return note


def build_payload(note):
    if note.ambiente == "producao" and not current_app.config.get(
        "FISCAL_PRODUCTION_ENABLED", False
    ):
        raise ValueError(
            "Produção bloqueada nesta instalação. Valide a tributação em homologação e habilite FISCAL_PRODUCTION_ENABLED=1 no servidor."
        )
    snap = note.snapshot
    company = snap["empresa"]
    params = company["parametros"]
    crt = company["regime_tributario"]
    if crt not in {"1", "3"}:
        raise ValueError(
            "Esta versão suporta CRT 1 e 3. CRT 2/4 exige extensão tributária."
        )
    recipient = (
        json.loads(decrypt(note.destinatario_cifrado))
        if note.destinatario_cifrado
        else {}
    )
    if snap["delivery"] and not recipient:
        raise ValueError(
            "Complete os dados fiscais do destinatário desta tele-entrega na área fiscal antes de emitir."
        )
    gross = sum(i["preco"] * i["quantidade"] for i in snap["itens"])
    freight = snap["frete"]
    if gross <= 0 or freight < 0:
        raise ValueError("Valor de produtos ou frete inválido.")
    # Rateio em centavos, com resíduo no último item, mantendo a soma exata.
    allocated = 0
    if snap["total"] <= 0 or not snap["itens"]:
        raise ValueError("A comanda não possui itens tributáveis com valor positivo.")
    items = []
    for index, original in enumerate(snap["itens"], 1):
        rule = original.get("regra")
        if not rule:
            raise ValueError("Cadastre a tributação de: " + original["nome"])
        validate_rule(rule)
        cst = rule["icms_situacao_tributaria"]
        if (crt == "1" and cst not in {"102", "500"}) or (
            crt == "3" and cst not in {"00", "40", "41", "60"}
        ):
            raise ValueError(
                "CST/CSOSN incompatível com o regime de: " + original["nome"]
            )
        price, qty = original["preco"], original["quantidade"]
        total = price * qty
        share = (
            (freight - allocated)
            if index == len(snap["itens"])
            else freight * total // gross
        )
        allocated += share
        tax_base = total + share
        if price <= 0 or qty <= 0:
            raise ValueError(
                "Itens gratuitos ou quantidade inválida exigem tratamento fiscal específico."
            )
        item = {
            "numero_item": str(index),
            "codigo_produto": str(original["id"]),
            "descricao": original["nome"],
            "codigo_ncm": rule["codigo_ncm"],
            "cfop": rule["cfop"],
            "unidade_comercial": rule["unidade"],
            "unidade_tributavel": rule["unidade"],
            "quantidade_comercial": str(qty),
            "quantidade_tributavel": str(qty),
            "valor_unitario_comercial": amount(price),
            "valor_unitario_tributavel": amount(price),
            "valor_bruto": amount(total),
            "icms_origem": rule["icms_origem"],
            "icms_situacao_tributaria": cst,
        }
        if share:
            item["valor_frete"] = amount(share)
        if rule.get("cest"):
            item["cest"] = rule["cest"]
        if cst == "00":
            aliquota = rate(
                rule.get("icms_aliquota") or params.get("aliquota_icms", "")
            )
            item.update(
                icms_modalidade_base_calculo="3",
                icms_base_calculo=amount(tax_base),
                icms_aliquota=str(aliquota),
                icms_valor=amount(
                    int(
                        (Decimal(tax_base) * aliquota / 100).quantize(
                            Decimal(1), rounding=ROUND_HALF_UP
                        )
                    )
                ),
            )
        for prefix in ["pis", "cofins"]:
            item[prefix + "_situacao_tributaria"] = rule[
                prefix + "_situacao_tributaria"
            ]
            if rule[prefix + "_situacao_tributaria"] in {"01", "02"}:
                aliquota = rate(rule[prefix + "_aliquota_porcentual"])
                item[prefix + "_base_calculo"] = amount(tax_base)
                item[prefix + "_aliquota_porcentual"] = str(aliquota)
                item[prefix + "_valor"] = amount(
                    int(
                        (Decimal(tax_base) * aliquota / 100).quantize(
                            Decimal(1), rounding=ROUND_HALF_UP
                        )
                    )
                )
        items.append(item)
    if gross + freight != snap["total"]:
        raise ValueError(
            "Total fiscal diferente do recebimento. Confira descontos e acréscimos."
        )
    forms = {
        "dinheiro": "01",
        "credito": "03",
        "debito": "04",
        "pix": params.get("pix_codigo", "20"),
    }
    if snap["forma"] not in forms:
        raise ValueError("Forma de pagamento não suportada na emissão.")
    payment = {
        "forma_pagamento": forms[snap["forma"]],
        "valor_pagamento": amount(snap["total"]),
    }
    if snap["forma"] in {"credito", "debito", "pix"}:
        payment["tipo_integracao"] = "2"  # pagamento externo, sem TEF integrado
    if note.ambiente == "homologacao":
        items[0][
            "descricao"
        ] = "NOTA FISCAL EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
    payload = {
        "cnpj_emitente": company["cnpj"],
        "data_emissao": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(
            timespec="seconds"
        ),
        "natureza_operacao": "VENDA AO CONSUMIDOR",
        "indicador_inscricao_estadual_destinatario": "9",
        "modalidade_frete": "0" if snap["delivery"] else "9",
        "local_destino": "1",
        "presenca_comprador": "4" if snap["delivery"] else "1",
        "items": items,
        "formas_pagamento": [payment],
        "valor_produtos": amount(gross),
        "valor_frete": amount(freight),
        "valor_total": amount(snap["total"]),
    }
    payload.update(recipient)
    return payload


def clean_message(data):
    # Não persistir a resposta inteira: pode conter dados/credenciais do provedor.
    pieces = [data.get("mensagem_sefaz"), data.get("mensagem")]
    for e in data.get("erros", []) if isinstance(data.get("erros", []), list) else []:
        if isinstance(e, dict):
            pieces.append(e.get("mensagem"))
    return " · ".join(str(x) for x in pieces if isinstance(x, str))[:1500]


def apply_response(note, code, data):
    status = data.get("status")
    if status == "autorizado":
        key = str(data.get("chave_nfe", "")).removeprefix("NFe")
        if not re.fullmatch(r"\d{44}", key):
            note.status, note.mensagem = (
                "processando",
                "API retornou autorização sem chave válida. Consulte novamente.",
            )
            return
        note.status, note.chave_acesso = "autorizada", key
        note.danfe_url = safe_document_url(
            note.ambiente, data.get("caminho_danfe") or data.get("caminho_danfe_nfce")
        )
        note.xml_url = safe_document_url(
            note.ambiente, data.get("caminho_xml_nota_fiscal")
        )
    elif status in {"erro_autorizacao", "rejeitado", "rejeitada"}:
        note.status = "rejeitada"
    elif status == "cancelado":
        note.status = "cancelada"
    else:
        # HTTP 4xx isolado não prova rejeição SEFAZ (pode ser referência já usada).
        note.status = "processando"
    note.codigo_sefaz = str(data.get("status_sefaz") or "")[:10]
    note.mensagem = clean_message(data) or (
        "Consulte a API para conciliar esta referência."
        if note.status == "processando"
        else note.status.capitalize()
    )


def process_one(note_id):
    """Lease de 90s > timeout HTTP. Em caso de queda, só GET na recuperação."""
    db.session.rollback()
    lease = secrets.token_hex(16)
    at = now()
    result = db.session.execute(
        db.update(NotaFiscal)
        .where(
            NotaFiscal.id == note_id,
            NotaFiscal.status.in_(["pendente", "processando"]),
            db.or_(NotaFiscal.trava_ate.is_(None), NotaFiscal.trava_ate < at),
            NotaFiscal.proxima_consulta <= at,
        )
        .values(trava_id=lease, trava_ate=at + timedelta(seconds=90))
    )
    db.session.commit()
    if result.rowcount != 1:
        return False
    note = db.session.get(NotaFiscal, note_id)
    try:
        token = decrypt(note.token_cifrado)
        if not note.enviado_em:
            try:
                payload = build_payload(note)
            except ValueError as exc:
                note.status, note.mensagem = "erro_configuracao", str(exc)
                return True
            # Reserva número e snapshot antes do POST, sob write lock SQLite.
            db.session.rollback()
            db.session.execute(db.text("BEGIN IMMEDIATE"))
            note = db.session.get(NotaFiscal, note_id)
            if note.trava_id != lease or note.enviado_em:
                return False
            company = note.snapshot["empresa"]
            series = int(company["parametros"]["serie"])
            seq = db.session.scalar(
                db.select(FiscalSequencia).where(
                    FiscalSequencia.cnpj == company["cnpj"],
                    FiscalSequencia.ambiente == note.ambiente,
                    FiscalSequencia.serie == series,
                )
            )
            if not seq:
                raise ValueError("Configure a numeração fiscal antes de emitir.")
            if seq.proximo_numero > 999999999:
                raise ValueError(
                    "Numeração esgotada. Configure outra série após validar com o responsável fiscal."
                )
            note.numero, note.serie = seq.proximo_numero, series
            seq.proximo_numero += 1
            payload.update(numero=str(note.numero), serie=str(series))
            note.payload, note.enviado_em, note.status = (
                {"cifrado": encrypt(json.dumps(payload))},
                now(),
                "processando",
            )
            db.session.commit()
            code, data = call(
                note.ambiente, token, "POST", "/v2/nfce?ref=" + note.referencia, payload
            )
        else:
            config = db.session.get(ConfiguracoesFiscais, 1)
            if (
                config
                and config.ambiente == note.ambiente
                and config.cnpj == note.snapshot["empresa"]["cnpj"]
            ):
                token = decrypt(config.token_cifrado)
            ambiente, path = note.ambiente, nfce_path(note.referencia)
            db.session.commit()
            code, data = call(ambiente, token, "GET", path)
        db.session.expire(note)
        if note.trava_id != lease:
            return False
        apply_response(note, code, data)
        if code == 404:
            note.mensagem = "Referência ainda não localizada na API. Nenhum reenvio automático será feito; concilie com o provedor antes de reenviar."
    except (ProviderError, ValueError) as exc:
        note.mensagem = str(exc)
        if not note.enviado_em:
            note.status = "erro_configuracao"
        # Após qualquer POST incerto, nunca criar nova referência ou outro POST.
    finally:
        # Não manter transações abertas durante o intervalo entre consultas.
        if note.trava_id == lease:
            note.atualizado = now()
            note.proxima_consulta = now() + timedelta(seconds=60)
            note.trava_id, note.trava_ate = None, None
            db.session.commit()
        else:
            db.session.rollback()
    return True
