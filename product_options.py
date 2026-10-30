"""Opções de produtos por restaurante, com validação e preços no servidor."""

import hashlib
import json
import os
import secrets
from pathlib import Path
from flask import (
    Blueprint,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from config import DATA, data_dir
from models import db, Produto

bp = Blueprint("product_options", __name__)


def path_for(id):
    return data_dir(DATA) / "product-options" / f"{int(id)}.json"


def settings(id):
    path = path_for(id)
    if not path.exists():
        return {
            "groups": [],
            "notes": {
                "enabled": True,
                "label": "Observação",
                "placeholder": "Ex.: sem cebola",
            },
        }
    return json.loads(path.read_text(encoding="utf-8"))


def revision(product, config):
    value = json.dumps(
        [product.nome, product.preco, bool(product.ativo), config],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def public_product(product):
    config = settings(product.id)
    groups = []
    for group in config["groups"]:
        if group["enabled"]:
            groups.append(
                {**group, "choices": [c for c in group["choices"] if c["enabled"]]}
            )
    return dict(
        id=product.id,
        nome=product.nome,
        descricao=product.descricao or "",
        preco=product.preco,
        emoji=product.emoji,
        groups=groups,
        notes=config["notes"],
        version=revision(product, config),
    )


@bp.app_context_processor
def inject():
    return {"product_catalog": lambda products: [public_product(p) for p in products]}


def clean_config(data):
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("groups"), list)
        or len(data["groups"]) > 8
    ):
        abort(400, "Use no máximo oito grupos de opções por produto.")

    def text(value, label, limit=48):
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value.strip()) > limit
        ):
            abort(400, f"Preencha {label} com até {limit} caracteres.")
        return value.strip()

    def boolean(value):
        if type(value) is not bool:
            abort(400, "Opção de ativação inválida.")
        return value

    notes = data.get("notes", {})
    if not isinstance(notes, dict):
        abort(400, "Configuração de observação inválida.")
    result = {
        "groups": [],
        "notes": {
            "enabled": boolean(notes.get("enabled")),
            "label": text(notes.get("label"), "o título da observação"),
            "placeholder": text(
                notes.get("placeholder") or "Digite sua observação",
                "a dica da observação",
                100,
            ),
        },
    }
    used = set()
    for source in data["groups"]:
        if not isinstance(source, dict):
            abort(400, "Grupo inválido.")
        gid = source.get("id")
        if (
            not isinstance(gid, str)
            or not gid.isalnum()
            or not 1 <= len(gid) <= 40
            or gid in used
        ):
            abort(400, "Identificador de grupo inválido ou repetido.")
        used.add(gid)
        kind = source.get("type")
        if kind not in ("single", "multiple", "text"):
            abort(400, "Tipo de opção inválido.")
        required = boolean(source.get("required"))
        choices = source.get("choices")
        if not isinstance(choices, list) or len(choices) > 20:
            abort(400, "Use até vinte escolhas por grupo.")
        group = dict(
            id=gid,
            title=text(source.get("title"), "o título do grupo"),
            type=kind,
            enabled=boolean(source.get("enabled")),
            required=required,
            max=1,
            choices=[],
        )
        ids = set()
        for choice in choices if kind != "text" else []:
            if not isinstance(choice, dict):
                abort(400, "Escolha inválida.")
            cid = choice.get("id")
            price = choice.get("price")
            if (
                not isinstance(cid, str)
                or not cid.isalnum()
                or not 1 <= len(cid) <= 40
                or cid in ids
            ):
                abort(400, "Identificador de escolha inválido ou repetido.")
            ids.add(cid)
            if type(price) is not int or not 0 <= price <= 100000000:
                abort(400, "Informe um acréscimo válido, sem valor negativo.")
            group["choices"].append(
                dict(
                    id=cid,
                    label=text(choice.get("label"), "o nome da escolha", 60),
                    price=price,
                    enabled=boolean(choice.get("enabled")),
                )
            )
        enabled = sum(c["enabled"] for c in group["choices"])
        if kind != "text" and group["enabled"] and not enabled:
            abort(400, "Cada grupo exibido precisa ter pelo menos uma escolha visível.")
        if kind == "multiple":
            maximum = source.get("max")
            if type(maximum) is not int or not 1 <= maximum <= 20:
                abort(400, "O limite de escolhas deve estar entre 1 e 20.")
            group["max"] = maximum
        result["groups"].append(group)
    return result


def resolve_item(product, item):
    config = public_product(product)
    if config["groups"] and item.get("opcoes_versao") != config["version"]:
        abort(
            409,
            "As opções deste produto mudaram. Reabra o cardápio e escolha novamente.",
        )
    selected = item.get("opcoes", {})
    if not isinstance(selected, dict) or set(selected) - {
        g["id"] for g in config["groups"]
    }:
        abort(400, "Opções inválidas para este produto.")
    price, parts = product.preco, []
    for group in config["groups"]:
        value = selected.get(group["id"], "" if group["type"] == "text" else [])
        if group["type"] == "text":
            if not isinstance(value, str) or len(value) > 60:
                abort(400, f"Use até 60 caracteres em {group['title']}.")
            value = value.strip()
            if group["required"] and not value:
                abort(400, f"Preencha {group['title']}.")
            if value:
                parts.append(f"{group['title']}: {value}")
            continue
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            abort(400, "Seleção inválida.")
        if (
            len(value) != len(set(value))
            or len(value) > group["max"]
            or (group["required"] and not value)
        ):
            abort(400, f"Confira as escolhas de {group['title']}.")
        choices = {c["id"]: c for c in group["choices"]}
        if set(value) - set(choices):
            abort(400, "Uma escolha não está mais disponível.")
        chosen = [c for c in group["choices"] if c["id"] in value]
        price += sum(c["price"] for c in chosen)
        if chosen:
            parts.append(group["title"] + ": " + ", ".join(c["label"] for c in chosen))
    note = item.get("observacao", "")
    if not isinstance(note, str) or len(note) > 300:
        abort(400, "Observação inválida.")
    note = note.strip()
    if note and not config["notes"]["enabled"]:
        abort(400, "Este produto não permite observação livre.")
    if note:
        parts.append(
            (
                config["notes"]["label"] + ": "
                if parts or config["notes"]["label"] != "Observação"
                else ""
            )
            + note
        )
    result = " | ".join(parts)
    if len(result) > 300:
        abort(
            400,
            "As opções e observações devem somar até 300 caracteres. Resuma os textos.",
        )
    return price, result


@bp.route("/cadastros/produtos/<int:id>/opcoes", methods=["GET", "POST"])
def configure(id):
    if not g.user:
        return redirect(url_for("login"))
    if g.user.perfil != "admin":
        abort(403)
    product = db.get_or_404(Produto, id)
    config = settings(id)
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, "Configuração inválida.")
        if data.get("version") != revision(product, config):
            abort(
                409,
                "Este produto foi alterado em outra tela. Recarregue antes de salvar.",
            )
        config = clean_config(data)
        path = path_for(id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.stem + "-" + secrets.token_hex(8) + ".tmp")
        try:
            with temp.open("w", encoding="utf-8") as file:
                json.dump(config, file, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        return jsonify(ok=True, version=revision(product, config))
    return render_template(
        "product_options.html",
        product=product,
        config=config,
        version=revision(product, config),
    )
