"""Cria (ou redefine) a conta única do proprietário pelo terminal do servidor."""

import argparse
import getpass
import sqlite3
from uuid import uuid4
from pathlib import Path
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash
from config import DATA, Config
from platform_admin import Registry, utcnow, valid_email


def setup(reset=False):
    registry = Registry(DATA / "plataforma")
    existing = registry.owner()
    if existing and not reset:
        raise SystemExit(
            "Administrador geral já configurado. Para redefinir: python setup_geral.py --redefinir"
        )
    name = input("Seu nome: ").strip()
    try:
        email = valid_email(input("Seu e-mail (será usado para entrar): "))
        login = email
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    password = getpass.getpass("Senha (mínimo 12 caracteres): ")
    confirm = getpass.getpass("Repita a senha: ")
    if (
        not name
        or len(name) > 100
        or not login
        or len(login) > 254
        or not 12 <= len(password) <= 256
        or password != confirm
    ):
        raise SystemExit(
            "Dados inválidos ou senhas diferentes. Nenhuma conta foi alterada."
        )
    with registry.connect() as c:
        c.execute("BEGIN IMMEDIATE")
        if existing:
            c.execute(
                "UPDATE owner SET name=?,login=?,email=?,password=?,version=version+1 WHERE id=1",
                (name, login, email, generate_password_hash(password)),
            )
        else:
            c.execute(
                "INSERT INTO owner(id,name,login,email,password) VALUES(1,?,?,?,?)",
                (name, login, email, generate_password_hash(password)),
            )
        registry.audit(
            c,
            None,
            (
                "Redefinição do proprietário"
                if existing
                else "Configuração do proprietário"
            ),
        )
    # Adota o banco existente sem mover dados, chaves, fotos ou senhas.
    path = Path(make_url(Config.SQLALCHEMY_DATABASE_URI).database or "")
    if not existing and path.is_file():
        with sqlite3.connect(path) as database:
            initialized = database.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'"
            ).fetchone()
            admins = (
                database.execute(
                    "SELECT COUNT(*) FROM usuario WHERE perfil='admin'"
                ).fetchone()[0]
                if initialized
                else 0
            )
        if admins:
            with registry.connect() as c:
                id = uuid4().hex
                c.execute(
                    "INSERT INTO restaurants(id,slug,name,folder,database_uri,enabled,created) VALUES(?,?,?,?,?,0,?)",
                    (
                        id,
                        "restaurante-atual",
                        "Restaurante atual",
                        "__legacy__",
                        Config.SQLALCHEMY_DATABASE_URI,
                        utcnow().isoformat(),
                    ),
                )
                registry.audit(
                    c,
                    id,
                    "Adoção do restaurante existente",
                    "Sem plano: ativação necessária pelo proprietário",
                )
            print(
                "Restaurante existente preservado em /r/restaurante-atual/. Defina o plano no painel geral."
            )
    print("Conta geral configurada. Inicie o sistema e acesse /geral/login.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--redefinir", action="store_true")
    setup(parser.parse_args().redefinir)
