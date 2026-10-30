"""Atualização aditiva das bases cadastradas, com backup SQLite antes de alterar."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import inspect
from models import db, PedidoQR


def migrate_current():
    inspector = inspect(db.engine)
    if not inspector.has_table("pedido"):
        return None
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("Esta atualização requer SQLite.")
    pedido_columns = {x["name"] for x in inspector.get_columns("pedido")}
    item_columns = {x["name"] for x in inspector.get_columns("item")}
    needed = (
        "numero_mesa" not in pedido_columns
        or not {"visitante_id", "etapa"}.issubset(item_columns)
        or not inspector.has_table("pedido_qr")
    )
    if not needed:
        return None
    db.session.remove()
    path = Path(db.engine.url.database)
    backup = path.with_name(
        path.stem
        + "-backup-acessos-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        + ".db"
    )
    with sqlite3.connect(path) as src, sqlite3.connect(backup) as dst:
        src.backup(dst)
    with db.engine.begin() as conn:
        if "numero_mesa" not in pedido_columns:
            conn.exec_driver_sql(
                "ALTER TABLE pedido ADD COLUMN numero_mesa VARCHAR(40) NOT NULL DEFAULT ''"
            )
        if "visitante_id" not in item_columns:
            conn.exec_driver_sql(
                "ALTER TABLE item ADD COLUMN visitante_id INTEGER REFERENCES usuario(id)"
            )
        if "etapa" not in item_columns:
            conn.exec_driver_sql(
                "ALTER TABLE item ADD COLUMN etapa VARCHAR(20) NOT NULL DEFAULT 'aberto'"
            )
            conn.exec_driver_sql(
                "UPDATE item SET etapa=COALESCE((SELECT status FROM pedido WHERE pedido.id=item.pedido_id),'aberto')"
            )
        PedidoQR.__table__.create(conn, checkfirst=True)
    return backup


def main():
    from app import app, create_app
    from config import Config

    dispatcher = app.extensions["restaurant_platform"]
    seen = set()
    sites = dispatcher.registry.sites()
    for site in sites:
        with dispatcher.application(site).app_context():
            print(
                site["name"]
                + ": "
                + str(migrate_current() or "já atualizado / banco ainda vazio")
            )
            seen.add(str(db.engine.url))
    if Config.SQLALCHEMY_DATABASE_URI not in seen:
        original = create_app()
        with original.app_context():
            print(
                "Banco original: "
                + str(migrate_current() or "já atualizado / banco ainda vazio")
            )
    print(
        "Atualização concluída. Reinicie a aplicação. Preserve os backups e as chaves de instance."
    )


if __name__ == "__main__":
    main()
