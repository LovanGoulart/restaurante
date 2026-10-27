"""Servidor local com worker de push. Em hospedagem, use processos supervisionados."""

import multiprocessing
import os
from waitress import serve
from app import app
from push_worker import run

if __name__ == "__main__":
    multiprocessing.freeze_support()
    worker = multiprocessing.Process(target=run, daemon=True)
    worker.start()
    try:
        serve(
            app,
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5000")),
            threads=64,
            channel_timeout=60,
        )
    finally:
        worker.terminate()
        worker.join(5)
