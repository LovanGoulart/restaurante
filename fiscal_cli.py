"""Migração e processador fiscal para banco original e todos os restaurantes."""

import argparse
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import inspect
from models import db, now
from fiscal_models import ConfiguracoesFiscais, RegraFiscal, FiscalSequencia, NotaFiscal
from fiscal_service import process_one

TABLES = [ConfiguracoesFiscais, RegraFiscal, FiscalSequencia, NotaFiscal]
_original_app = None


def migrate_current():
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("Esta migração foi preparada para o SQLite do projeto.")
    inspector = inspect(db.engine)
    if not inspector.has_table("pedido"):
        raise RuntimeError(
            "Banco de pedidos ausente. Não inicialize um banco vazio para substituir o existente."
        )
    if all(inspector.has_table(m.__tablename__) for m in TABLES):
        return None
    db.session.remove()
    path = Path(db.engine.url.database)
    backup = path.with_name(
        path.stem
        + "-backup-fiscal-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        + ".db"
    )
    with sqlite3.connect(path) as src, sqlite3.connect(backup) as dst:
        src.backup(dst)
    with db.engine.begin() as connection:
        for model in TABLES:
            model.__table__.create(connection, checkfirst=True)
    return backup


def process_batch(limit=25):
    if not inspect(db.engine).has_table("nota_fiscal"):
        return 0
    ids = list(
        db.session.scalars(
            db.select(NotaFiscal.id)
            .where(
                NotaFiscal.status.in_(["pendente", "processando"]),
                NotaFiscal.proxima_consulta <= now(),
                db.or_(NotaFiscal.trava_ate.is_(None), NotaFiscal.trava_ate < now()),
            )
            .order_by(NotaFiscal.proxima_consulta, NotaFiscal.id)
            .limit(limit)
        )
    )
    db.session.rollback()
    done = 0
    for id in ids:
        try:
            done += bool(process_one(id))
        except Exception:
            # Nada de traceback/payload/token em logs de produção. Lease expira para recuperação.
            db.session.rollback()
            print(
                f"Nota local {id}: falha interna. Verifique banco/chave fiscal. Sem reenvio automático de POST.",
                flush=True,
            )
        finally:
            db.session.remove()
    return done


def applications(slug):
    global _original_app
    from app import app, create_app
    from config import Config

    dispatcher = app.extensions["restaurant_platform"]
    sites = dispatcher.registry.sites()
    selected = [s for s in sites if not slug or s["slug"] == slug]
    if slug and not selected:
        raise RuntimeError(
            "Restaurante não encontrado. Use o identificador do link /r/IDENTIFICADOR/."
        )
    seen = set()
    for site in selected:
        seen.add(site["database_uri"])
        yield site["slug"], dispatcher.application(site)
    from sqlalchemy.engine import make_url

    original_path = make_url(Config.SQLALCHEMY_DATABASE_URI).database
    if (
        not slug
        and Config.SQLALCHEMY_DATABASE_URI not in seen
        and original_path
        and Path(original_path).is_file()
    ):
        if _original_app is None:
            _original_app = create_app()
        yield "original", _original_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["migrar", "processar"])
    parser.add_argument(
        "--restaurante",
        help="Identificador do restaurante no link; omitido = todas as bases.",
    )
    parser.add_argument(
        "--continuo",
        action="store_true",
        help="Manter o processador em execução (tarefa Always-on/systemd).",
    )
    args = parser.parse_args()
    if args.acao == "migrar":
        for name, app in applications(args.restaurante):
            with app.app_context():
                print(
                    name
                    + ": "
                    + str(migrate_current() or "tabelas fiscais já instaladas")
                )
        return
    try:
        while True:
            # Atualiza a lista para incluir restaurantes criados após iniciar o worker.
            for name, app in applications(args.restaurante):
                with app.app_context():
                    done = process_batch()
                    if done:
                        print(f"{name}: {done} documento(s) processado(s).", flush=True)
            if not args.continuo:
                break
            time.sleep(5)
    except KeyboardInterrupt:
        print("Processador encerrado.")


if __name__ == "__main__":
    main()
