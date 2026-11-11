"""Cria somente quatro tabelas de fidelidade, com backup SQLite antes da mudança."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from loyalty_models import FidelidadeConfig, FidelidadeRecompensa, FidelidadePedido, FidelidadeMovimento

TABLES = [m.__table__ for m in (FidelidadeConfig, FidelidadeRecompensa, FidelidadePedido, FidelidadeMovimento)]


class IncompatibleDatabase(ValueError):
    pass


def migrate_file(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"Banco não encontrado: {path}")
    with sqlite3.connect(str(path)) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"usuario", "cliente", "produto", "pedido", "pedido_online"} <= tables:
            raise IncompatibleDatabase(f"Banco não é um restaurante compatível: {path}")
        if all(t.name in tables for t in TABLES):
            return None
        backup = path.with_name(path.stem + "-antes-fidelidade-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".db")
        with sqlite3.connect(str(backup)) as dest:
            conn.backup(dest)
    engine = create_engine("sqlite:///" + str(path))
    try:
        with engine.begin() as conn:
            for table in TABLES:
                table.create(conn, checkfirst=True)
    finally:
        engine.dispose()
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--banco", help="Caminho de um restaurante.db específico")
    args = parser.parse_args()
    if args.banco:
        paths = [Path(args.banco)]
    elif os.environ.get("DATABASE_URL"):
        url = make_url(os.environ["DATABASE_URL"])
        if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
            raise SystemExit("Esta atualização usa o SQLite do projeto. Informe --banco com um arquivo válido.")
        paths = [Path(url.database)]
    else:
        root = Path(__file__).resolve().parent / "instance"
        paths = ([root / "restaurante.db"] if (root / "restaurante.db").is_file() else []) + sorted(
            (root / "plataforma" / "restaurantes").glob("*/restaurante.db"))
    if not paths:
        raise SystemExit("Nenhum banco encontrado. Use --banco com o caminho do restaurante.db.")
    failures = 0
    completed = 0
    for path in paths:
        try:
            backup = migrate_file(path)
            completed += 1
            print(f"OK: {path}" + (f"\nBackup: {backup}" if backup else " (já atualizado)"))
        except IncompatibleDatabase as exc:
            if args.banco or os.environ.get("DATABASE_URL"):
                failures += 1
                print(f"ERRO: {exc}")
            else:
                print(f"IGNORADO, sem alterações: {exc}")
        except Exception as exc:
            failures += 1
            print(f"ERRO: {exc}")
    raise SystemExit(1 if failures or not completed else 0)


if __name__ == "__main__":
    main()
