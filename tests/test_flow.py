import unittest
from app import create_app
from models import db, Usuario, Categoria, Produto, Pedido
from werkzeug.security import generate_password_hash


class Flow(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "SECRET_KEY": "test",
            }
        )
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        for role in ["admin", "garcom", "cozinha"]:
            db.session.add(
                Usuario(
                    nome=role,
                    login="admin@example.com" if role == "admin" else role,
                    senha=generate_password_hash("test-password"),
                    perfil=role,
                )
            )
        c = Categoria(nome="Pratos")
        db.session.add(c)
        db.session.flush()
        db.session.add(Produto(nome="Prato", preco=2590, categoria_id=c.id))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, role):
        self.client.get("/login")
        with self.client.session_transaction() as s:
            token = s["csrf"]
        self.client.post(
            "/login",
            data={
                "login": "admin@example.com" if role == "admin" else role,
                "senha": "test-password",
                "csrf": token,
            },
        )
        self.client.get("/")

        if role == "admin":
            import time

            with self.client.session_transaction() as session:
                session["management_grants"] = {
                    key: time.time() + 300
                    for key in [
                        "produtos",
                        "categorias",
                        "usuarios",
                        "clientes",
                        "loja",
                        "relatorios",
                    ]
                }

    def post(self, path, data=None, json=None):
        with self.client.session_transaction() as s:
            token = s["csrf"]
        return self.client.post(
            path,
            data={**(data or {}), "csrf": token} if json is None else None,
            json=json,
            headers={"X-CSRF-Token": token},
        )

    def test_full_flow(self):
        self.login("garcom")
        self.assertEqual(self.client.get("/caixa").status_code, 403)
        r = self.post(
            "/api/pedidos",
            json={
                "mesa": "08",
                "numero_mesa": "08",
                "itens": [{"id": 1, "quantidade": 2, "observacao": "Sem sal"}],
            },
        )
        self.assertEqual(r.status_code, 201)
        id = r.json["id"]
        self.assertEqual(
            self.post(
                f"/api/pedidos/{id}/status", json={"status": "em_preparo"}
            ).status_code,
            403,
        )
        self.login("cozinha")
        self.assertEqual(self.client.get("/pdv").status_code, 403)
        for status in ["em_preparo", "pronto"]:
            self.assertEqual(
                self.post(
                    f"/api/pedidos/{id}/status", json={"status": status}
                ).status_code,
                200,
            )
        self.assertEqual(
            self.post(
                f"/api/pedidos/{id}/status", json={"status": "entregue"}
            ).status_code,
            403,
        )
        self.login("garcom")
        self.assertEqual(
            self.post(
                f"/api/pedidos/{id}/status", json={"status": "entregue"}
            ).status_code,
            200,
        )
        self.login("admin")
        self.assertEqual(
            self.post(f"/api/pedidos/{id}/pagar", json={"forma": "pix"}).status_code,
            409,
        )
        self.assertEqual(
            self.post("/caixa", data={"acao": "abrir", "valor": "100"}).status_code, 302
        )
        self.assertEqual(
            self.post(f"/api/pedidos/{id}/pagar", json={"forma": "pix"}).status_code,
            200,
        )
        self.assertEqual(
            self.post(f"/api/pedidos/{id}/pagar", json={"forma": "pix"}).status_code,
            409,
        )
        self.assertEqual(db.session.get(Pedido, id).total, 5180)
        for page in [
            "/pdv",
            "/pedidos",
            "/dashboard",
            "/caixa",
            "/cadastros/produtos",
            "/cadastros/categorias",
            "/cadastros/usuarios",
        ]:
            self.assertEqual(self.client.get(page).status_code, 200, page)
        self.assertEqual(
            self.post("/caixa", data={"acao": "fechar", "valor": "100"}).status_code,
            302,
        )

    def test_csrf_and_validation(self):
        self.login("admin")
        self.assertEqual(self.client.post("/api/pedidos", json={}).status_code, 400)
        self.assertEqual(
            self.post(
                "/api/pedidos",
                json={
                    "mesa": "1",
                    "numero_mesa": "1",
                    "itens": [{"id": 1, "quantidade": -1}],
                },
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post(
                "/cadastros/produtos",
                data={"nome": "Teste", "preco": "nan", "categoria_id": "1"},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post("/caixa", data={"acao": "abrir", "valor": "10"}).status_code, 302
        )
        self.assertEqual(
            self.post("/caixa", data={"acao": "abrir", "valor": "10"}).status_code, 409
        )
        self.assertEqual(
            self.post(
                "/caixa",
                data={"acao": "sangria", "valor": "11", "descricao": "Retirada"},
            ).status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
