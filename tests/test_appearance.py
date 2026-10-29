import unittest
import tempfile
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from PIL import Image
from app import create_app
from models import db, Usuario, Produto, Categoria, Pedido
from werkzeug.security import generate_password_hash
import appearance


class AppearanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(appearance, "DATA", Path(self.tmp.name))
        self.patch.start()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        db.session.add_all(
            [
                Usuario(
                    id=1,
                    nome="Admin",
                    login="admin",
                    senha=generate_password_hash("test-password"),
                    perfil="admin",
                ),
                Usuario(
                    id=2, nome="Garçom", login="garcom", senha="x", perfil="garcom"
                ),
                Categoria(id=1, nome="Pratos"),
            ]
        )
        db.session.flush()
        db.session.add(Produto(id=1, nome="Prato", preco=1000, categoria_id=1))
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as s:
            s["uid"] = 1
            s["csrf"] = "test"

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.patch.stop()
        self.tmp.cleanup()

    def test_identity_and_permissions(self):
        data = dict(
            csrf="test",
            name="Restaurante Teste",
            title="Nova capa",
            subtitle="Descrição",
            navy="#112233",
            orange="#aa3300",
            accent="#ff6600",
            bg="#eeeeee",
        )
        self.assertEqual(
            self.client.post("/personalizacao", data=data).status_code, 302
        )
        for route in ["/pedidos", "/personalizacao", "/pdv", "/cardapio"]:
            r = self.client.get(route)
            self.assertEqual(r.status_code, 200)
            self.assertIn(b"Restaurante Teste", r.data)
        with self.client.session_transaction() as s:
            s["uid"] = 2
        self.assertEqual(self.client.get("/personalizacao").status_code, 403)
        self.assertEqual(
            self.client.post("/personalizacao", data=data).status_code, 403
        )
        self.assertEqual(self.client.get("/inicio").status_code, 403)

    def test_photo_validation_and_removal(self):
        data = dict(
            csrf="test",
            action="photo",
            product_id="1",
            photo=(BytesIO(b"<svg></svg>"), "fake.png"),
        )
        self.assertEqual(
            self.client.post("/personalizacao", data=data).status_code, 400
        )
        b = BytesIO()
        Image.new("RGB", (30, 30), "red").save(b, "PNG")
        b.seek(0)
        self.assertEqual(
            self.client.post(
                "/personalizacao",
                data=dict(
                    csrf="test", action="photo", product_id="1", photo=(b, "test.png")
                ),
            ).status_code,
            302,
        )
        name = appearance.settings()["photos"]["1"]
        response = self.client.get("/media/" + name)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertIn(name.encode(), self.client.get("/cardapio").data)
        self.client.post(
            "/personalizacao",
            data=dict(csrf="test", action="photo", product_id="1", remove="on"),
        )
        self.assertNotIn("1", appearance.settings()["photos"])

    def test_orders_home_and_sort(self):
        states = ["entregue", "em_preparo", "pronto", "aberto", "saiu_entrega"]
        db.session.add_all(
            [
                Pedido(mesa=str(i), usuario_id=1, status=state, pago=False)
                for i, state in enumerate(states)
            ]
        )
        db.session.commit()
        self.assertEqual(self.client.get("/").location, "/pedidos")
        self.assertEqual(self.client.get("/inicio").location, "/pedidos")
        response = self.client.get("/api/pedidos")
        self.assertEqual(
            [p["status"] for p in response.json],
            ["entregue", "pronto", "em_preparo", "aberto", "saiu_entrega"],
        )
        response = self.client.get("/pedidos")
        self.assertIn(b"order-detail-content", response.data)
        self.assertNotIn(b'href="/inicio"', response.data)

    def test_dashboard_payment_then_status(self):
        states = ["entregue", "aberto", "em_preparo", "pronto", "saiu_entrega"]
        for paid in [True, False]:
            for state in states:
                db.session.add(
                    Pedido(
                        mesa=("PAGO-" if paid else "PENDENTE-") + state,
                        usuario_id=1,
                        status=state,
                        pago=paid,
                    )
                )
        db.session.commit()
        html = self.client.get("/dashboard").data.decode()
        expected = [
            prefix + state
            for prefix in ["PENDENTE-", "PAGO-"]
            for state in ["pronto", "em_preparo", "aberto", "saiu_entrega", "entregue"]
        ]
        positions = [html.index(label) for label in expected]
        self.assertEqual(positions, sorted(positions))

    def test_icon_picker_and_br_assets(self):
        response = self.client.get("/cadastros/produtos")
        self.assertIn(b"data-product-icon", response.data)
        self.assertIn(b"br-fields.js", response.data)
