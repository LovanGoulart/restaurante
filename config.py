import os, secrets
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "instance"
DATA.mkdir(exist_ok=True)
key = DATA / "secret.key"
if not key.exists():
    try:
        with key.open("x") as f:
            f.write(secrets.token_hex(32))
        key.chmod(0o600)
    except FileExistsError:
        pass


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or key.read_text().strip()
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + str(
        DATA / "restaurante.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"
    MAX_CONTENT_LENGTH = 1024 * 1024
    FISCAL_PRODUCTION_ENABLED = os.environ.get("FISCAL_PRODUCTION_ENABLED") == "1"


def data_dir(default=DATA):
    """Pasta privada da aplicação atual; preserva o padrão em scripts legados."""
    from flask import current_app, has_app_context

    return (
        Path(current_app.config.get("DATA_DIR") or default)
        if has_app_context()
        else Path(default)
    )
