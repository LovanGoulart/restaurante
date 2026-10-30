"""Identidade visual e painel administrativo."""

import json
import os
import re
import secrets
from io import BytesIO
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    abort,
    send_from_directory,
)
from PIL import Image, ImageOps, UnidentifiedImageError
from config import DATA, data_dir
from models import db, Produto, Pedido
from customers import role, store

bp = Blueprint("appearance", __name__)
DEFAULTS = {
    "navy": "#101c32",
    "orange": "#c6421c",
    "accent": "#ff8355",
    "bg": "#edf1f7",
    "title": "Bom atendimento. Pedido no ponto.",
    "subtitle": "Escolha os itens, informe a mesa e pronto.",
    "photos": {},
    "cover": "",
}


def settings():
    path = data_dir(DATA) / "appearance.json"
    return (
        {**DEFAULTS, **json.loads(path.read_text())}
        if path.exists()
        else dict(DEFAULTS)
    )


def save(data):
    path = data_dir(DATA) / ("appearance-" + secrets.token_hex(8) + ".tmp")
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(path, data_dir(DATA) / "appearance.json")
    finally:
        path.unlink(missing_ok=True)


def upload(field):
    file = request.files.get(field)
    if not file or not file.filename:
        return None
    raw = file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        abort(400, "Cada imagem deve ter no máximo 5 MB.")
    try:
        with Image.open(BytesIO(raw)) as source:
            if (
                source.format not in ("JPEG", "PNG", "WEBP")
                or source.width * source.height > 20000000
            ):
                raise ValueError()
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1920, 1920))
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        abort(400, "Envie uma imagem JPG, PNG ou WebP válida, com até 20 megapixels.")
    folder = data_dir(DATA) / "media"
    folder.mkdir(exist_ok=True)
    name = secrets.token_hex(16) + ".jpg"
    image.save(folder / name, "JPEG", quality=88)
    return name


@bp.get("/media/<name>")
def media(name):
    if not re.fullmatch(r"[0-9a-f]{32}\.jpg", name):
        abort(404)
    return send_from_directory(data_dir(DATA) / "media", name)


@bp.app_context_processor
def inject():
    return dict(appearance=settings(), restaurant_name=store().nome)


@bp.route("/personalizacao", methods=["GET", "POST"])
@role("admin")
def customize():
    if request.method == "POST":
        data = settings()
        if request.form.get("action") == "photo":
            product = db.get_or_404(Produto, request.form.get("product_id", type=int))
            photo = upload("photo")
            data["photos"] = dict(data["photos"])
            if request.form.get("remove"):
                data["photos"].pop(str(product.id), None)
            elif photo:
                data["photos"][str(product.id)] = photo
            else:
                abort(400, "Selecione uma foto.")
        else:
            name = request.form.get("name", "").strip()
            if not name or len(name) > 100:
                abort(400, "Informe um nome com até 100 caracteres.")
            for key in ("navy", "orange", "accent", "bg"):
                value = request.form.get(key, "")
                if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                    abort(400, "Cor inválida.")
                data[key] = value
            for key in ("title", "subtitle"):
                value = request.form.get(key, "").strip()
                if len(value) > 180:
                    abort(400, "Os textos da capa devem ter até 180 caracteres.")
                data[key] = value
            cover = upload("cover")
            if request.form.get("remove_cover"):
                data["cover"] = ""
            elif cover:
                data["cover"] = cover
            loja = store()
            loja.nome = name
            db.session.add(loja)
            db.session.commit()
        save(data)
        return redirect(url_for("appearance.customize", saved=1))
    return render_template(
        "personalizacao.html",
        products=db.session.scalars(db.select(Produto).order_by(Produto.nome)).all(),
    )


@bp.get("/inicio")
@role("admin")
def overview():
    return redirect(url_for("pedidos"))
