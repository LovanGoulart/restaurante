"""Painel do proprietário e despacho de restaurantes com bancos isolados."""

import calendar
import hashlib
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import shutil
from cryptography.fernet import Fernet
from threading import RLock
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    abort,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
)
from werkzeug.exceptions import NotFound
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.wrappers import Response

from config import BASE, DATA, Config

BR = ZoneInfo("America/Sao_Paulo")
PLANS = {1: "1 mês", 3: "3 meses", 6: "6 meses", 12: "1 ano"}


def valid_email(value):
    value = (value or "").strip()
    if len(value) > 254 or value.count("@") != 1:
        raise ValueError("Informe um e-mail válido.")
    local, domain = value.rsplit("@", 1)
    try:
        domain = domain.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise ValueError("Informe um e-mail válido.") from None
    if (
        not 1 <= len(local) <= 64
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
        or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local)
        or len(domain) > 253
        or "." not in domain
        or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part)
            for part in domain.split(".")
        )
        or not re.fullmatch(r"[a-z]{2,63}|xn--[a-z0-9-]+", domain.rsplit(".", 1)[-1])
    ):
        raise ValueError("Informe um e-mail válido.")
    return (local + "@" + domain).lower()


def administrator_profile(form):
    """Valida dados obrigatórios sem guardar CPF em texto puro."""
    from customer_security import cpf_valido, cpf_digits, data_nascimento

    name = (form.get("admin_nome") or form.get("nome", "")).strip()
    if not 2 <= len(name) <= 100:
        raise ValueError(
            "Informe o nome completo do administrador (2 a 100 caracteres)."
        )
    cpf = form.get("cpf", "")
    if not cpf_valido(cpf):
        raise ValueError(
            "CPF inválido. Confira os 11 dígitos e os dígitos verificadores."
        )
    birthday = data_nascimento(form.get("nascimento"))
    result = dict(nome=name, cpf=cpf_digits(cpf), nascimento=birthday.isoformat())
    for field, label, limit in [
        ("endereco", "rua/avenida", 160),
        ("numero", "número do endereço", 20),
        ("bairro", "bairro", 100),
    ]:
        value = form.get(field, "").strip()
        if not value or len(value) > limit:
            raise ValueError("Preencha corretamente o campo " + label + ".")
        result[field] = value
    return result


def utcnow():
    return datetime.now(timezone.utc)


def add_months(value, months):
    local = value.astimezone(BR)
    year, month = divmod(local.year * 12 + local.month - 1 + months, 12)
    return local.replace(
        year=year,
        month=month + 1,
        day=min(local.day, calendar.monthrange(year, month + 1)[1]),
    ).astimezone(timezone.utc)


def active(site):
    return bool(
        site
        and site["enabled"]
        and site["expires"]
        and datetime.fromisoformat(site["expires"]) > utcnow()
    )


class Registry:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "plataforma.db"
        with self.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS owner (
              id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL,
              login TEXT NOT NULL UNIQUE, password TEXT NOT NULL,
              version INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS restaurants (
              id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
              folder TEXT NOT NULL, database_uri TEXT NOT NULL,
              expires TEXT, enabled INTEGER NOT NULL DEFAULT 0,
              created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit (
              id INTEGER PRIMARY KEY, restaurant_id TEXT, action TEXT NOT NULL,
              details TEXT NOT NULL DEFAULT '', created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts (key TEXT NOT NULL, created REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS attempts_key ON attempts(key, created);
            CREATE TABLE IF NOT EXISTS admin_contacts (
              restaurant_id TEXT NOT NULL, user_id INTEGER NOT NULL, email TEXT NOT NULL,
              PRIMARY KEY(restaurant_id,user_id));
            """)
            if "email" not in [row[1] for row in c.execute("PRAGMA table_info(owner)")]:
                c.execute("ALTER TABLE owner ADD COLUMN email TEXT NOT NULL DEFAULT ''")
            if "version" not in [
                row[1] for row in c.execute("PRAGMA table_info(admin_contacts)")
            ]:
                c.execute(
                    "ALTER TABLE admin_contacts ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
                )

            columns = {r[1] for r in c.execute("PRAGMA table_info(admin_contacts)")}
            for name in ("cpf_cifrado", "nascimento", "endereco", "numero", "bairro"):
                if name not in columns:
                    c.execute(
                        f"ALTER TABLE admin_contacts ADD COLUMN {name} TEXT NOT NULL DEFAULT ''"
                    )

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=20)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def contact(self, id, uid):
        with self.connect() as c:
            row = c.execute(
                "SELECT * FROM admin_contacts WHERE restaurant_id=? AND user_id=?",
                (id, uid),
            ).fetchone()
            return dict(row) if row else {}

    def admin_id(self, id, email):
        with self.connect() as c:
            row = c.execute(
                "SELECT user_id FROM admin_contacts WHERE restaurant_id=? AND lower(email)=lower(?)",
                (id, email),
            ).fetchone()
            return row[0] if row else None

    def save_contact(self, c, id, uid, email, profile):
        duplicate = c.execute(
            "SELECT user_id FROM admin_contacts WHERE restaurant_id=? AND lower(email)=lower(?) AND user_id!=?",
            (id, email, uid),
        ).fetchone()
        if duplicate:
            raise ValueError(
                "Este e-mail já pertence a outro administrador deste restaurante."
            )
        cipher = Fernet(self.profile_key()).encrypt(profile["cpf"].encode()).decode()
        c.execute(
            """INSERT INTO admin_contacts(restaurant_id,user_id,email,cpf_cifrado,nascimento,endereco,numero,bairro)
          VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(restaurant_id,user_id) DO UPDATE SET
          email=excluded.email,cpf_cifrado=excluded.cpf_cifrado,nascimento=excluded.nascimento,
          endereco=excluded.endereco,numero=excluded.numero,bairro=excluded.bairro,version=admin_contacts.version+1""",
            (
                id,
                uid,
                email,
                cipher,
                profile["nascimento"],
                profile["endereco"],
                profile["numero"],
                profile["bairro"],
            ),
        )

    def profile_key(self):
        path = self.root / "administrator-data.key"
        if not path.exists():
            with self.connect() as c:
                if c.execute(
                    "SELECT 1 FROM admin_contacts WHERE cpf_cifrado!='' LIMIT 1"
                ).fetchone():
                    raise RuntimeError(
                        "Restaure administrator-data.key do backup antes de alterar CPFs."
                    )
            try:
                with path.open("xb") as f:
                    f.write(Fernet.generate_key())
                path.chmod(0o600)
            except FileExistsError:
                pass
        return path.read_bytes().strip()

    def sites(self):
        with self.connect() as c:
            return [
                self.resolve(dict(r))
                for r in c.execute("SELECT * FROM restaurants ORDER BY created DESC")
            ]

    def resolve(self, site):
        if site["folder"] == "__legacy__":
            site["folder"] = str(DATA.resolve())
            site["database_uri"] = Config.SQLALCHEMY_DATABASE_URI
        else:
            folder = self.root / "restaurantes" / site["id"]
            site["folder"] = str(folder)
            site["database_uri"] = "sqlite:///" + str(folder / "restaurante.db")
        return site

    def site(self, slug=None, id=None):
        with self.connect() as c:
            row = c.execute(
                "SELECT * FROM restaurants WHERE " + ("slug=?" if slug else "id=?"),
                (slug or id,),
            ).fetchone()
            return self.resolve(dict(row)) if row else None

    def owner(self):
        with self.connect() as c:
            row = c.execute("SELECT * FROM owner WHERE id=1").fetchone()
            return dict(row) if row else None

    def admin_email(self, id, uid):
        with self.connect() as c:
            row = c.execute(
                "SELECT email FROM admin_contacts WHERE restaurant_id=? AND user_id=?",
                (id, uid),
            ).fetchone()
            return row["email"] if row else ""

    def admin_version(self, id, uid):
        with self.connect() as c:
            row = c.execute(
                "SELECT version FROM admin_contacts WHERE restaurant_id=? AND user_id=?",
                (id, uid),
            ).fetchone()
            return row["version"] if row else 0

    def audit(self, c, id, action, details=""):
        c.execute(
            "INSERT INTO audit(restaurant_id, action, details, created) VALUES(?,?,?,?)",
            (id, action, details, utcnow().isoformat()),
        )


def file_key(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "secret.key"
    if not path.exists():
        try:
            with path.open("x") as f:
                f.write(secrets.token_hex(32))
            path.chmod(0o600)
        except FileExistsError:
            pass
    return path.read_text().strip()


class RestaurantDispatcher:
    def __init__(self, platform, factory, registry):
        self.platform, self.factory, self.registry = platform, factory, registry
        self.apps = {}
        self.lock = RLock()

    def application(self, site):
        with self.lock:
            if site["id"] not in self.apps:
                prefix = "/r/" + site["slug"]
                app = self.factory(
                    {
                        "SQLALCHEMY_DATABASE_URI": site["database_uri"],
                        "DATA_DIR": site["folder"],
                        "SECRET_KEY": file_key(site["folder"]),
                        "SESSION_COOKIE_NAME": "restaurant_" + site["id"],
                        "SESSION_COOKIE_PATH": prefix + "/",
                        "APPLICATION_ROOT": prefix,
                        "RESTAURANT_ID": site["id"],
                        "ACCESS_CHECK": lambda id=site["id"]: active(
                            self.registry.site(id=id)
                        ),
                        "ADMIN_CHECK": lambda uid, id=site[
                            "id"
                        ]: self.valid_admin_email(id, uid),
                        "ADMIN_LOOKUP": lambda email, id=site[
                            "id"
                        ]: self.registry.admin_id(id, email),
                        "ADMIN_VERSION": lambda uid, id=site[
                            "id"
                        ]: self.registry.admin_version(id, uid),
                    }
                )
                self.apps[site["id"]] = app
            return self.apps[site["id"]]

    def valid_admin_email(self, id, uid):
        try:
            return bool(valid_email(self.registry.admin_email(id, uid)))
        except ValueError:
            return False

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        match = re.match(r"^/r/([a-z0-9][a-z0-9-]{1,48}[a-z0-9])(?=/|$)", path)
        if not match:
            return self.platform(environ, start_response)
        site = self.registry.site(slug=match.group(1))
        if not site:
            return NotFound()(environ, start_response)
        if not active(site):
            if "/api/" in path:
                response = Response(
                    '{"error":"Acesso inativo. Solicite a renovação ao administrador geral."}',
                    status=403,
                    content_type="application/json",
                )
            else:
                response = Response(
                    "<!doctype html><html lang=pt-BR><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Acesso inativo</title><body style='font:18px system-ui;padding:40px;background:#f1f5f9;color:#20344e'><h1>Acesso inativo</h1><p>O acesso deste restaurante está suspenso, sem plano ou com prazo encerrado.</p><p>Entre em contato com o administrador geral para renovar.</p></body></html>",
                    status=403,
                    content_type="text/html; charset=utf-8",
                )
            response.headers["Cache-Control"] = "no-store"
            return response(environ, start_response)
        prefix = match.group(0)
        if path == prefix:
            response = Response(
                status=308,
                headers={
                    "Location": prefix
                    + "/"
                    + (
                        "?" + environ["QUERY_STRING"]
                        if environ.get("QUERY_STRING")
                        else ""
                    )
                },
            )
            return response(environ, start_response)
        environ = environ.copy()
        environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + prefix
        environ["PATH_INFO"] = path[len(prefix) :] or "/"
        return self.application(site)(environ, start_response)


def create_platform(factory, root=None):
    registry = Registry(root or DATA / "plataforma")
    app = Flask(
        "restaurante_platform",
        template_folder=str(BASE / "templates"),
        static_folder=str(BASE / "static"),
    )
    app.config.update(
        SECRET_KEY=file_key(registry.root),
        SESSION_COOKIE_NAME="manager_owner",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=Config.SESSION_COOKIE_SECURE,
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    dispatcher = RestaurantDispatcher(app.wsgi_app, factory, registry)
    app.extensions["restaurant_platform"] = dispatcher
    app.wsgi_app = dispatcher

    @app.before_request
    def load_owner():
        if request.endpoint == "static":
            g.owner = None
            return
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(32)
        owner = registry.owner()
        g.owner = (
            owner
            if owner
            and session.get("owner_id") == 1
            and session.get("owner_version") == owner["version"]
            else None
        )
        if request.method == "POST" and not secrets.compare_digest(
            str(session["csrf"]), str(request.form.get("csrf", ""))
        ):
            abort(400, "Sessão expirada. Atualize a página.")

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.template_filter("plan_date")
    def plan_date(value):
        return (
            datetime.fromisoformat(value).astimezone(BR).strftime("%d/%m/%Y %H:%M")
            if value
            else "Sem plano"
        )

    @app.context_processor
    def context():
        return dict(owner=g.owner, csrf=session["csrf"], plans=PLANS, is_active=active)

    def owner_only(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not g.owner:
                return redirect(url_for("owner_login"))
            return fn(*args, **kwargs)

        return wrapped

    @app.get("/")
    @app.get("/login")
    def home():
        return redirect(url_for("owner_panel") if g.owner else url_for("owner_login"))

    @app.get("/sw.js")
    def retire_legacy_worker():
        # Retira apenas o worker antigo da raiz; os workers /r/<slug>/ são preservados.
        response = Response(
            "self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.registration.unregister()));",
            mimetype="application/javascript",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/geral/login", methods=["GET", "POST"])
    def owner_login():
        if g.owner:
            return redirect(url_for("owner_panel"))
        error = None
        if request.method == "POST":
            try:
                login = valid_email(
                    request.form.get("email") or request.form.get("login", "")
                )
            except ValueError:
                login = ""
            key = hashlib.sha256((request.remote_addr or "").encode()).hexdigest()
            now = utcnow().timestamp()
            with registry.connect() as c:
                c.execute("BEGIN IMMEDIATE")
                c.execute("DELETE FROM attempts WHERE created<?", (now - 900,))
                count = c.execute(
                    "SELECT COUNT(*) FROM attempts WHERE key=?", (key,)
                ).fetchone()[0]
                if count >= 10:
                    abort(429, "Muitas tentativas. Aguarde 15 minutos.")
                c.execute("INSERT INTO attempts VALUES(?,?)", (key, now))
            owner = registry.owner()
            valid = check_password_hash(
                (
                    owner["password"]
                    if owner
                    else generate_password_hash("not-a-real-password")
                ),
                request.form.get("senha", ""),
            )
            if owner and login and login == owner["email"].lower() and valid:
                session.clear()
                session.update(
                    owner_id=1,
                    owner_version=owner["version"],
                    csrf=secrets.token_hex(32),
                )
                with registry.connect() as c:
                    c.execute("DELETE FROM attempts WHERE key=?", (key,))
                return redirect(url_for("owner_panel"))
            error = (
                "E-mail ou senha incorretos. Use o e-mail cadastrado no setup_geral.py."
            )
        return render_template(
            "geral_login.html", error=error, configured=bool(registry.owner())
        )

    @app.post("/geral/sair")
    @owner_only
    def owner_logout():
        session.clear()
        return redirect(url_for("owner_login"))

    @app.get("/geral")
    @owner_only
    def owner_panel():
        sites = registry.sites()
        with registry.connect() as c:
            audit = c.execute(
                "SELECT a.*, r.name FROM audit a LEFT JOIN restaurants r ON r.id=a.restaurant_id ORDER BY a.id DESC LIMIT 15"
            ).fetchall()
        return render_template(
            "geral.html",
            sites=sites,
            audit=audit,
            active_count=sum(active(s) for s in sites),
        )

    @app.post("/geral/restaurantes")
    @owner_only
    def create_restaurant():
        from models import db, Usuario, Loja

        name = request.form.get("nome", "").strip()
        slug = request.form.get("slug", "").strip().lower()
        password = request.form.get("senha", "")
        try:
            email = valid_email(request.form.get("email"))
            profile = administrator_profile(request.form)
            login = email
        except ValueError as exc:
            abort(400, str(exc))
        months = request.form.get("meses", type=int)
        if (
            not name
            or len(name) > 100
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,48}[a-z0-9]", slug)
        ):
            abort(
                400,
                "Informe o nome do restaurante e um identificador do link com 3 a 50 letras minúsculas, números e hífens. Não digite o endereço residencial no link.",
            )
        if not login or not 10 <= len(password) <= 256 or months not in PLANS:
            abort(
                400,
                "Informe a senha inicial de 10 a 256 caracteres e selecione o período de acesso.",
            )
        id = uuid4().hex
        folder = registry.root / "restaurantes" / id
        site = dict(
            id=id,
            slug=slug,
            name=name,
            folder=str(folder),
            database_uri="sqlite:///" + str(folder / "restaurante.db"),
            expires=add_months(utcnow(), months).isoformat(),
            enabled=1,
            created=utcnow().isoformat(),
        )
        try:
            with registry.connect() as c:
                c.execute("BEGIN IMMEDIATE")
                if c.execute(
                    "SELECT id FROM restaurants WHERE slug=?", (slug,)
                ).fetchone():
                    abort(409, "Esse endereço de restaurante já existe.")
                tenant = dispatcher.application(site)
                with tenant.app_context():
                    db.create_all()
                    admin = Usuario(
                        nome=profile["nome"],
                        login=login,
                        senha=generate_password_hash(password),
                        perfil="admin",
                        ativo=True,
                    )
                    db.session.add(admin)
                    db.session.add(Loja(id=1, nome=name))
                    db.session.commit()
                    admin_id = admin.id
                    from setup_push import setup

                    setup(email)
                c.execute(
                    "INSERT INTO restaurants(id,slug,name,folder,database_uri,expires,enabled,created) VALUES(:id,:slug,:name,:folder,:database_uri,:expires,:enabled,:created)",
                    site,
                )
                registry.save_contact(c, id, admin_id, email, profile)
                registry.audit(c, id, "Cadastro", f"Plano de {months} meses")
        except Exception as exc:
            failed = dispatcher.apps.pop(id, None)
            if failed:
                with failed.app_context():
                    db.session.remove()
                    db.engine.dispose()
            shutil.rmtree(folder, ignore_errors=True)
            from werkzeug.exceptions import HTTPException

            if isinstance(exc, HTTPException):
                raise
            app.logger.error("Falha ao cadastrar restaurante: %s", type(exc).__name__)
            abort(
                503,
                "Não foi possível concluir o cadastro. Confira se o servidor permite gravar na pasta instance e se as dependências foram instaladas. Nenhum restaurante foi liberado; seus dados continuam no formulário para tentar novamente.",
            )
        return redirect(url_for("owner_panel", saved=1))

    @app.post("/geral/restaurantes/<id>/plano")
    @owner_only
    def plan(id):
        action = request.form.get("acao")
        with registry.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM restaurants WHERE id=?", (id,)).fetchone()
            if not row:
                abort(404)
            if action == "renovar":
                months = request.form.get("meses", type=int)
                if months not in PLANS:
                    abort(400, "Plano inválido.")
                base = (
                    max(utcnow(), datetime.fromisoformat(row["expires"]))
                    if row["expires"]
                    else utcnow()
                )
                end = add_months(base, months)
                c.execute(
                    "UPDATE restaurants SET expires=?,enabled=1 WHERE id=?",
                    (end.isoformat(), id),
                )
                registry.audit(
                    c, id, "Renovação", f"{months} meses; até {end.isoformat()}"
                )
            elif action == "suspender":
                c.execute("UPDATE restaurants SET enabled=0 WHERE id=?", (id,))
                registry.audit(c, id, "Suspensão")
            elif action == "ativar":
                if (
                    not row["expires"]
                    or datetime.fromisoformat(row["expires"]) <= utcnow()
                ):
                    abort(409, "Renove o plano antes de ativar.")
                c.execute("UPDATE restaurants SET enabled=1 WHERE id=?", (id,))
                registry.audit(c, id, "Reativação")
            else:
                abort(400, "Ação inválida.")
        return redirect(url_for("owner_panel", saved=1))

    @app.route("/geral/restaurantes/<id>/administradores", methods=["GET", "POST"])
    @owner_only
    def admins(id):
        from models import db, Usuario

        site = registry.site(id=id)
        if not site:
            abort(404)
        return_path = url_for("admins", id=id, saved=1)
        users = []
        with dispatcher.application(site).app_context():
            if request.method == "POST":
                uid = request.form.get("id", type=int)
                action = request.form.get("acao")
                if action in {"criar", "perfil", "email"}:
                    try:
                        email = valid_email(request.form.get("email"))
                        profile = (
                            administrator_profile(request.form)
                            if action != "email"
                            else None
                        )
                    except ValueError as exc:
                        abort(400, str(exc))
                    other = registry.admin_id(id, email)
                    if other and other != uid:
                        abort(409, "E-mail já cadastrado neste restaurante.")
                if action == "criar":
                    password = request.form.get("senha", "")
                    if not 10 <= len(password) <= 256:
                        abort(400, "Use senha de 10 a 256 caracteres.")
                    if db.session.scalar(
                        db.select(Usuario.id).where(Usuario.login == email)
                    ):
                        abort(
                            409,
                            "Este e-mail já está em uso como login neste restaurante.",
                        )
                    user = Usuario(
                        nome=profile["nome"],
                        login=email,
                        senha=generate_password_hash(password),
                        perfil="admin",
                        ativo=True,
                    )
                    db.session.add(user)
                    db.session.flush()
                    uid = user.id
                else:
                    user = db.session.get(Usuario, uid)
                    if not user or user.perfil != "admin":
                        abort(404)
                if action == "perfil":
                    user.nome = profile["nome"]
                elif action == "senha":
                    password = request.form.get("senha", "")
                    if not 10 <= len(password) <= 256:
                        abort(400, "Use senha de 10 a 256 caracteres.")
                    user.senha = generate_password_hash(password)
                elif action in {"ativar", "desativar"}:
                    user.ativo = action == "ativar"
                elif action not in {"criar", "email"}:
                    abort(400, "Ação inválida.")
                with registry.connect() as c:
                    if action in {"criar", "perfil"}:
                        registry.save_contact(c, id, uid, email, profile)
                    elif action == "email":
                        c.execute(
                            "INSERT INTO admin_contacts(restaurant_id,user_id,email) VALUES(?,?,?) ON CONFLICT(restaurant_id,user_id) DO UPDATE SET email=excluded.email,version=admin_contacts.version+1",
                            (id, uid, email),
                        )
                    if action in {"senha", "desativar"}:
                        c.execute(
                            "UPDATE admin_contacts SET version=version+1 WHERE restaurant_id=? AND user_id=?",
                            (id, uid),
                        )
                    registry.audit(c, id, "Administrador: " + action, f"Usuário {uid}")
                    db.session.commit()
                return redirect(return_path)
            for u in db.session.scalars(
                db.select(Usuario).where(Usuario.perfil == "admin").order_by(Usuario.id)
            ):
                contact = registry.contact(id, u.id)
                cpf = ""
                if contact.get("cpf_cifrado"):
                    cpf = (
                        Fernet(registry.profile_key())
                        .decrypt(contact["cpf_cifrado"].encode())
                        .decode()
                    )
                    cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
                users.append(
                    dict(
                        contact,
                        id=u.id,
                        nome=u.nome,
                        login=u.login,
                        ativo=u.ativo,
                        cpf=cpf,
                    )
                )
        return render_template("geral_admins.html", site=site, users=users)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(429)
    @app.errorhandler(503)
    def error(exc):
        if request.accept_mimetypes.best == "application/json":
            return jsonify(error=exc.description), exc.code
        return render_template("geral_error.html", message=exc.description), exc.code

    return app
