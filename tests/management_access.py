"""Confirmação de senha por área administrativa, também aplicada aos endpoints."""

import hashlib
import time
from urllib.parse import urlsplit
from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash
from werkzeug.exceptions import HTTPException
from customer_security import throttle
from models import db, TentativaAcesso

bp = Blueprint("management_access", __name__)
TTL = 300


@bp.errorhandler(HTTPException)
def json_error(exc):
    if request.is_json:
        db.session.rollback()
        return jsonify(error=exc.description), exc.code
    return render_template("error.html", message=exc.description), exc.code


for _code in (400, 401, 403, 404, 409, 429, 503):
    bp.register_error_handler(_code, json_error)


def scope_for(path):
    if path == "/fiscal" or path.startswith("/fiscal/"):
        return "fiscal"
    if path.startswith("/relatorios"):
        return "relatorios"
    if path.startswith("/loja"):
        return "loja"
    if path.startswith("/clientes") or path.startswith("/api/clientes"):
        return "clientes"
    if path.startswith("/cadastros/"):
        kind = path.split("/")[2]
        if kind in {"produtos", "categorias", "usuarios"}:
            return kind
    return None


def safe_destination(value):
    parsed = urlsplit(value or "")
    prefix = request.script_root
    path = parsed.path
    if prefix and path.startswith(prefix + "/"):
        path = path[len(prefix) :]
    if (
        parsed.scheme
        or parsed.netloc
        or not path.startswith("/")
        or path.startswith("//")
        or not scope_for(path)
    ):
        abort(400, "Destino inválido.")
    # Só páginas conhecidas; exportação exige liberação da área correspondente.
    allowed = {
        "/relatorios-vendas",
        "/loja",
        "/fiscal",
        "/clientes",
        "/cadastros/produtos",
        "/cadastros/categorias",
        "/cadastros/usuarios",
    }
    if path not in allowed:
        abort(400, "Área inválida.")
    return path


def guard():
    scope = scope_for(request.path)
    if not scope or not g.user or g.user.perfil != "admin":
        return
    grant = session.get("management_grants", {}).get(scope, 0)
    if not isinstance(grant, (int, float)) or grant < time.time():
        if (
            request.method != "GET"
            or request.path.startswith("/api/")
            or "export" in request.path
        ):
            if request.is_json:
                return (
                    jsonify(
                        error="Confirme a senha do administrador para salvar nesta área.",
                        code="management_auth_required",
                        scope=scope,
                    ),
                    403,
                )
            abort(403, "Confirme a senha do administrador para acessar esta área.")
        path = request.path
        if scope == "fiscal":
            path = "/fiscal"
        if scope == "produtos":
            path = "/cadastros/produtos"
        if scope == "relatorios":
            path = "/relatorios-vendas"
        return redirect(
            url_for("management_access.unlock", destino=request.script_root + path)
        )


@bp.route("/acesso-restrito", methods=["GET", "POST"])
def unlock():
    if not g.user:
        if request.is_json:
            return jsonify(error="Sua sessão terminou. Entre novamente."), 401
        return redirect(url_for("login"))
    if g.user.perfil != "admin":
        abort(403)
    data = request.get_json(silent=True) if request.is_json else request.form
    if request.is_json and not isinstance(data, dict):
        abort(400, "Envie um objeto JSON válido.")
    destination = safe_destination(
        data.get("destino") if request.is_json else request.values.get("destino")
    )
    error = None
    if request.method == "GET":
        # Cada clique nos menus protegidos volta a pedir a senha.
        grants = dict(session.get("management_grants", {}))
        grants.pop(scope_for(destination), None)
        session["management_grants"] = grants
    if request.method == "POST":
        scope = "management-password:" + str(g.user.id)
        throttle(scope, 8, 900)
        if check_password_hash(
            g.user.senha,
            data.get("senha", "") if isinstance(data.get("senha", ""), str) else "",
        ):
            # Só erros acumulam tentativas; navegar por vários menus não bloqueia o titular.
            key = hashlib.sha256(
                (scope + "|" + (request.remote_addr or "local")).encode()
            ).hexdigest()
            db.session.execute(
                db.delete(TentativaAcesso).where(TentativaAcesso.chave == key)
            )
            db.session.commit()
            grants = dict(session.get("management_grants", {}))
            grants[scope_for(destination)] = time.time() + TTL
            session["management_grants"] = grants
            if request.is_json:
                return jsonify(ok=True)
            return redirect(request.script_root + destination)
        if request.is_json:
            return (
                jsonify(error="Senha incorreta. Informe a senha deste administrador."),
                403,
            )
        error = "Senha incorreta. Informe a senha deste administrador."
    return render_template(
        "acesso_restrito.html",
        destination=request.script_root + destination,
        error=error,
    )


@bp.post("/bloquear-gestao")
def lock():
    session.pop("management_grants", None)
    return redirect(url_for("pedidos"))
