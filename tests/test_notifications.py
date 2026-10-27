import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import create_app
from models import (
    db,
    Usuario,
    Categoria,
    Produto,
    Pedido,
    Notificacao,
    PushSubscription,
    PushDelivery,
)
from werkzeug.security import generate_password_hash
from push_worker import process_pending
from migrate import migrate
from setup_push import setup


class Notifications(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "SECRET_KEY": "test",
                "SSE_DURATION": 0.025,
                "SSE_INTERVAL": 0.005,
            }
        )
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        for role, name in [
            ("admin", "admin"),
            ("garcom", "garcom"),
            ("cozinha", "cozinha"),
            ("garcom", "outro"),
        ]:
            db.session.add(
                Usuario(
                    nome=name,
                    login=name,
                    senha=generate_password_hash("test-password"),
                    perfil=role,
                )
            )
        cat = Categoria(nome="Pratos")
        db.session.add(cat)
        db.session.flush()
        db.session.add(Produto(nome="Prato", preco=2590, categoria_id=cat.id))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, name):
        self.client.get("/login")
        with self.client.session_transaction() as s:
            csrf = s["csrf"]
        self.client.post(
            "/login", data={"login": name, "senha": "test-password", "csrf": csrf}
        )
        self.client.get("/")

    def post(self, path, data):
        with self.client.session_transaction() as s:
            csrf = s["csrf"]
        return self.client.post(path, json=data, headers={"X-CSRF-Token": csrf})

    def order(self):
        self.login("garcom")
        r = self.post(
            "/api/pedidos", {"mesa": "08", "itens": [{"id": 1, "quantidade": 2}]}
        )
        self.assertEqual(r.status_code, 201)
        return r.json["id"]

    def ready(self, id):
        original = self.client
        self.client = self.app.test_client()
        self.login("cozinha")
        for status in ["em_preparo", "pronto"]:
            self.assertEqual(
                self.post(f"/api/pedidos/{id}/status", {"status": status}).status_code,
                200,
            )
        self.client = original

    def subscription(self):
        return {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-only",
            "keys": {
                "p256dh": base64.urlsafe_b64encode(b"\x04" + b"x" * 64)
                .decode()
                .rstrip("="),
                "auth": base64.urlsafe_b64encode(b"x" * 16).decode().rstrip("="),
            },
        }

    def subscribe(self):
        with (
            patch("notifications.push_config", return_value={"public_key": "test"}),
            patch("notifications.worker_online", return_value=True),
        ):
            return self.post("/api/push/subscribe", self.subscription())

    def test_scoped_sse_replay_and_alerts(self):
        id = self.order()
        self.ready(id)
        self.login("garcom")
        result = self.client.get("/api/notificacoes").json
        self.assertEqual(result["nao_lidas"], 1)
        self.assertEqual(result["items"][0]["tipo"], "pronto")
        response = self.client.get("/api/eventos?after=0", buffered=True)
        body = response.get_data(as_text=True)
        self.assertEqual(response.mimetype, "text/event-stream")
        self.assertIn("event: connected", body)
        self.assertIn("Pedido pronto para retirar", body)
        events = [
            json.loads(line[6:])
            for line in body.splitlines()
            if line.startswith("data: ") and line != "data: {}"
        ]
        self.assertEqual(len(events), 3)
        last = max(e["id"] for e in events)
        replay = self.client.get(
            "/api/eventos?after=0", headers={"Last-Event-ID": str(last)}, buffered=True
        ).get_data(as_text=True)
        self.assertNotIn("event: pedido", replay)
        self.login("outro")
        self.assertEqual(self.client.get("/api/notificacoes").json["items"], [])
        self.assertIn(
            "event: pedido",
            self.client.get("/api/eventos?after=0", buffered=True).get_data(
                as_text=True
            ),
        )

    def test_read_only_own_notifications(self):
        id = self.order()
        self.ready(id)
        self.login("garcom")
        item = self.client.get("/api/notificacoes").json["items"][0]
        self.assertEqual(
            self.post("/api/notificacoes/lidas", {"ate": item["id"]}).status_code, 200
        )
        self.assertEqual(self.client.get("/api/notificacoes").json["nao_lidas"], 0)
        self.login("admin")
        self.assertGreater(self.client.get("/api/notificacoes").json["nao_lidas"], 0)

    def test_authentication_and_csrf(self):
        for path in ["/api/eventos", "/api/notificacoes", "/api/push/config"]:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.login("garcom")
        self.assertEqual(
            self.client.post("/api/push/subscribe", json={}).status_code, 400
        )
        self.assertEqual(self.client.get("/api/eventos?after=bad").status_code, 400)

    def test_push_validation_queue_and_dispatch(self):
        self.login("garcom")
        bad = self.subscription()
        bad["endpoint"] = "https://127.0.0.1/private"
        with (
            patch("notifications.push_config", return_value={"public_key": "test"}),
            patch("notifications.worker_online", return_value=True),
        ):
            self.assertEqual(self.post("/api/push/subscribe", bad).status_code, 400)
        self.assertEqual(self.subscribe().status_code, 200)
        id = self.post(
            "/api/pedidos", {"mesa": "08", "itens": [{"id": 1, "quantidade": 1}]}
        ).json["id"]
        self.ready(id)
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(PushDelivery)), 1
        )
        calls = []
        with patch(
            "push_worker.push_config",
            return_value={"private_key": "fake", "subject": "mailto:test@example.com"},
        ):
            self.assertEqual(process_pending(send=lambda **kw: calls.append(kw)), 1)
        payload = json.loads(calls[0]["data"])
        self.assertEqual(payload["title"], "Pedido pronto para retirar")
        self.assertIn("08", payload["body"])
        self.assertEqual(db.session.scalar(db.select(PushDelivery)).estado, "enviado")

    def test_push_stale_and_retry(self):
        self.login("garcom")
        self.assertEqual(self.subscribe().status_code, 200)
        id = self.post(
            "/api/pedidos", {"mesa": "09", "itens": [{"id": 1, "quantidade": 1}]}
        ).json["id"]
        self.ready(id)

        class Failed(Exception):
            pass

        def fail(**kwargs):
            raise Failed("network unavailable")

        with patch(
            "push_worker.push_config",
            return_value={"private_key": "fake", "subject": "mailto:test@example.com"},
        ):
            self.assertEqual(process_pending(send=fail), 0)
            task = db.session.scalar(db.select(PushDelivery))
            self.assertEqual(task.estado, "pendente")
            self.assertEqual(task.tentativas, 1)
            self.login("garcom")
            self.post(f"/api/pedidos/{id}/status", {"status": "entregue"})
            from datetime import datetime, timezone

            task.proxima = datetime(2000, 1, 1, tzinfo=timezone.utc)
            db.session.commit()
            self.assertEqual(process_pending(send=fail), 0)
            self.assertEqual(db.session.get(PushDelivery, task.id).estado, "cancelado")

    def test_logout_revokes_device(self):
        self.login("garcom")
        self.assertEqual(self.subscribe().status_code, 200)
        self.assertEqual(self.post("/logout", {}).status_code, 302)
        self.assertFalse(db.session.scalar(db.select(PushSubscription)).ativo)

    def test_pwa_assets_and_private_cache(self):
        response = self.client.get("/sw.js")
        self.assertEqual(response.mimetype, "application/javascript")
        response.close()
        manifest = self.client.get("/manifest.webmanifest")
        self.assertEqual(manifest.mimetype, "application/manifest+json")
        data = json.loads(manifest.data)
        manifest.close()
        self.assertEqual(data["display"], "standalone")
        for icon in data["icons"]:
            response = self.client.get(icon["src"])
            self.assertEqual(response.status_code, 200)
            response.close()
        for asset in ["/static/js/pwa.js", "/static/offline.html"]:
            response = self.client.get(asset)
            self.assertEqual(response.status_code, 200)
            response.close()
        self.login("garcom")
        r = self.client.get("/pdv")
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        self.assertIn(b'id="mobile-cart"', r.data)
        response = self.client.get("/sw.js")
        sw = response.get_data(as_text=True)
        response.close()
        self.assertRegex(sw, r"e\.request\.mode\s*===\s*[\"']navigate[\"']")
        self.assertNotIn("c.put(e.request", sw)


class Migration(unittest.TestCase):
    def test_additive_migration_keeps_existing_data(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "old.db"
            app = create_app(
                {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(path)}
            )
            with app.app_context():
                tables = [
                    t
                    for t in db.metadata.sorted_tables
                    if t.name
                    not in [
                        "notificacao",
                        "push_subscription",
                        "push_delivery",
                        "cliente",
                        "loja",
                        "pedido_online",
                        "envio_pedido",
                        "tentativa_acesso",
                        "entrega",
                    ]
                ]
                db.metadata.create_all(db.engine, tables=tables)
                db.session.add(
                    Usuario(
                        nome="Existente",
                        login="existente",
                        senha="preservar",
                        perfil="admin",
                    )
                )
                db.session.commit()
                backup = migrate()
                self.assertTrue(backup.is_file())
                self.assertEqual(
                    db.session.scalar(db.select(Usuario)).senha, "preservar"
                )
                with sqlite3.connect(str(backup)) as conn:
                    self.assertEqual(
                        conn.execute("select nome from usuario").fetchone()[0],
                        "Existente",
                    )
                self.assertIsNone(migrate())
                db.session.remove()
                db.engine.dispose()

    def test_vapid_keys_are_valid_and_preserved(self):
        from py_vapid import Vapid

        with (
            tempfile.TemporaryDirectory() as temp,
            patch("setup_push.DATA", Path(temp)),
        ):
            setup("test@example.com")
            original = (Path(temp) / "vapid.json").read_bytes()
            data = json.loads(original)
            key = Vapid.from_string(data["private_key"])
            self.assertTrue(key.public_key)
            import base64, os
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            from pywebpush import WebPusher

            client = (
                ec.generate_private_key(ec.SECP256R1())
                .public_key()
                .public_bytes(
                    serialization.Encoding.X962,
                    serialization.PublicFormat.UncompressedPoint,
                )
            )
            encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
            encrypted = WebPusher(
                {
                    "endpoint": "https://fcm.googleapis.com/fcm/send/test",
                    "keys": {"p256dh": encode(client), "auth": encode(os.urandom(16))},
                }
            ).encode(b"Test notification")
            self.assertIn("body", encrypted)
            self.assertGreater(len(encrypted["body"]), len(b"Test notification"))
            setup("other@example.com")
            self.assertEqual((Path(temp) / "vapid.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
