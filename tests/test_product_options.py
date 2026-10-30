import sys, json, time, tempfile, unittest
from pathlib import Path
from app import create_app
from models import db, Usuario, Produto, Categoria, Pedido
from product_options import public_product, settings, path_for
from werkzeug.security import generate_password_hash


class Options(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "DATA_DIR": self.temp.name,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///"
                + str(Path(self.temp.name) / "db.sqlite"),
            }
        )
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        for role in ["admin", "garcom", "cozinha"]:
            db.session.add(
                Usuario(
                    nome=role,
                    login=role,
                    senha=generate_password_hash("test-password"),
                    perfil=role,
                )
            )
        db.session.add(Categoria(nome="Pizzas"))
        db.session.flush()
        db.session.add(Produto(nome="Pizza de teste", preco=5000, categoria_id=1))
        db.session.commit()
        self.client = self.app.test_client()
        self.login(1)

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.ctx.pop()
        self.temp.cleanup()

    def login(self, uid):
        with self.client.session_transaction() as s:
            s["uid"] = uid
            s["csrf"] = "token"
            s["management_grants"] = {"produtos": time.time() + 300}

    def post(self, path, data):
        return self.client.post(path, json=data, headers={"X-CSRF-Token": "token"})

    def config(self):
        return {
            "version": public_product(db.session.get(Produto, 1))["version"],
            "notes": {
                "enabled": True,
                "label": "Observação",
                "placeholder": "Sem cebola",
            },
            "groups": [
                {
                    "id": "size",
                    "title": "Tamanho e fatias",
                    "type": "single",
                    "required": True,
                    "enabled": True,
                    "max": 1,
                    "choices": [
                        {
                            "id": "small",
                            "label": "Broto · 4 fatias",
                            "enabled": True,
                            "price": 0,
                        },
                        {
                            "id": "large",
                            "label": "Grande · 12 fatias",
                            "enabled": True,
                            "price": 1500,
                        },
                        {
                            "id": "hidden",
                            "label": "Oculta",
                            "enabled": False,
                            "price": 0,
                        },
                    ],
                },
                {
                    "id": "border",
                    "title": "Borda",
                    "type": "single",
                    "required": False,
                    "enabled": True,
                    "max": 1,
                    "choices": [
                        {
                            "id": "cheese",
                            "label": "Requeijão",
                            "enabled": True,
                            "price": 500,
                        }
                    ],
                },
            ],
        }

    def save(self, c=None):
        r = self.post("/cadastros/produtos/1/opcoes", c or self.config())
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        return r

    def item(self):
        return {
            "id": 1,
            "quantidade": 2,
            "opcoes_versao": public_product(db.session.get(Produto, 1))["version"],
            "opcoes": {"size": ["large"], "border": ["cheese"]},
            "observacao": "Sem cebola",
            "preco": 1,
        }

    def order(self, item):
        return self.post(
            "/api/pedidos", {"comanda": "8", "numero_mesa": "4", "itens": [item]}
        )

    def test_price_and_snapshot(self):
        self.save()
        self.login(2)
        r = self.order(self.item())
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        p = db.session.get(Pedido, r.json["id"])
        self.assertEqual(p.total, 14000)
        self.assertEqual(p.itens[0].preco, 7000)
        self.assertIn("Grande · 12 fatias", p.itens[0].observacao)
        self.assertIn("Requeijão", p.itens[0].observacao)
        self.login(1)
        c = self.config()
        c["groups"][0]["choices"][1]["price"] = 9000
        self.save(c)
        db.session.refresh(p)
        self.assertEqual(p.total, 14000)

    def test_required_hidden_duplicate_stale_tamper(self):
        self.save()
        i = self.item()
        i["opcoes"]["size"] = []
        self.assertEqual(self.order(i).status_code, 400)
        i = self.item()
        i["opcoes"]["size"] = ["hidden"]
        self.assertEqual(self.order(i).status_code, 400)
        i = self.item()
        i["opcoes"]["size"] = ["large", "large"]
        self.assertEqual(self.order(i).status_code, 400)
        i = self.item()
        i["opcoes"]["inventado"] = ["large"]
        self.assertEqual(self.order(i).status_code, 400)
        i = self.item()
        i["opcoes_versao"] = "antiga"
        self.assertEqual(self.order(i).status_code, 409)
        self.assertEqual(db.session.scalar(db.select(db.func.count(Pedido.id))), 0)

    def test_notes_and_group_visibility(self):
        c = self.config()
        c["groups"][0]["enabled"] = False
        c["notes"]["enabled"] = False
        self.save(c)
        i = self.item()
        i["opcoes"].pop("size")
        i["observacao"] = ""
        self.assertEqual(self.order(i).status_code, 201)
        i = self.item()
        i["opcoes"].pop("size")
        self.assertEqual(self.order(i).status_code, 400)

    def test_permissions_csrf_stale_settings_and_no_schema(self):
        c = self.config()
        self.save(c)
        self.assertEqual(self.post("/cadastros/produtos/1/opcoes", c).status_code, 409)
        self.assertEqual(
            self.client.post(
                "/cadastros/produtos/1/opcoes", json=self.config()
            ).status_code,
            400,
        )
        for uid in (2, 3):
            self.login(uid)
            self.assertEqual(
                self.post("/cadastros/produtos/1/opcoes", self.config()).status_code,
                403,
            )
        self.login(1)
        with self.client.session_transaction() as s:
            s["management_grants"] = {}
        self.assertEqual(
            self.post("/cadastros/produtos/1/opcoes", self.config()).status_code, 403
        )
        self.assertTrue(path_for(1).is_relative_to(Path(self.temp.name)))

    def test_text_multiple_limits_and_bad_prices(self):
        c = self.config()
        c["groups"][0]["type"] = "multiple"
        c["groups"][0]["max"] = 2
        c["groups"].append(
            {
                "id": "allergy",
                "title": "Alergia",
                "type": "text",
                "required": True,
                "enabled": True,
                "max": 1,
                "choices": [],
            }
        )
        self.save(c)
        i = self.item()
        i["opcoes"]["size"] = ["small", "large"]
        i["opcoes"]["allergy"] = "Nenhuma"
        self.assertEqual(self.order(i).status_code, 201)
        i = self.item()
        self.assertEqual(self.order(i).status_code, 400)
        c = self.config()
        c["groups"][0]["choices"][0]["price"] = -1
        self.assertEqual(self.post("/cadastros/produtos/1/opcoes", c).status_code, 400)

    def test_catalog_screens_render(self):
        self.save()
        for uid, path in [(1, "/pdv"), (2, "/pdv")]:
            self.login(uid)
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200)
            self.assertIn('id="product-picker"', r.get_data(as_text=True))
        self.login(3)
        self.assertEqual(self.client.get("/pdv").status_code, 403)
        self.login(1)
        r = self.client.get("/cardapio")
        self.assertEqual(r.status_code, 200)
        self.assertIn('data-category-section="1"', r.get_data(as_text=True))

    def test_restaurants_keep_options_separate(self):
        self.save()
        other = Path(self.temp.name) / "other"
        other.mkdir()
        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "other",
                "DATA_DIR": str(other),
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )
        with app.app_context():
            db.create_all()
            db.session.add(Categoria(nome="Outra categoria"))
            db.session.flush()
            db.session.add(Produto(nome="Outro produto", preco=500, categoria_id=1))
            db.session.commit()
            product = public_product(db.session.get(Produto, 1))
            self.assertEqual(product["groups"], [])
            self.assertEqual(product["preco"], 500)
            db.session.remove()
            db.engine.dispose()
        self.assertEqual(len(settings(1)["groups"]), 2)


if __name__ == "__main__":
    unittest.main()
