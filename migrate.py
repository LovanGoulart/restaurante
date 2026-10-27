"""Migração aditiva v3.2: preserva o banco e cria somente as tabelas novas."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from sqlalchemy import inspect
from app import app
from models import (
    db,
    Notificacao,
    PushSubscription,
    PushDelivery,
    Cliente,
    Loja,
    PedidoOnline,
    EnvioPedido,
    TentativaAcesso,
    Entrega,
)


def migrate():
    inspector = inspect(db.engine)
    if "pedido" not in inspector.get_table_names():
        raise RuntimeError(
            "Banco não inicializado. Execute init_db.py para uma instalação nova."
        )
    missing = [
        m
        for m in (
            Notificacao,
            PushSubscription,
            PushDelivery,
            Cliente,
            Loja,
            PedidoOnline,
            EnvioPedido,
            TentativaAcesso,
            Entrega,
        )
        if not inspector.has_table(m.__tablename__)
    ]
    if not missing:
        return None
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("Esta migração é específica para SQLite.")
    path = Path(db.engine.url.database)
    backup = None
    if path.is_file():
        backup = path.with_name(
            path.stem
            + "-backup-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
            + ".db"
        )
        with sqlite3.connect(str(path)) as src, sqlite3.connect(str(backup)) as dest:
            src.backup(dest)
    for model in missing:
        model.__table__.create(db.engine, checkfirst=True)
    return backup


if __name__ == "__main__":
    with app.app_context():
        backup = migrate()
        print(
            "Atualização concluída. "
            + ("Backup: " + str(backup) if backup else "Esquema já atualizado.")
        )
