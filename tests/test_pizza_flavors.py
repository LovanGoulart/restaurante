"""Média dos sabores, limites por tamanho e preservação do preço do pedido."""

import unittest
import test_product_options as fixtures
from models import db, Produto, Pedido
from product_options import public_product


class PizzaFlavors(unittest.TestCase):
    setUp = fixtures.Options.setUp
    tearDown = fixtures.Options.tearDown
    login = fixtures.Options.login
    post = fixtures.Options.post
    save = fixtures.Options.save
    order = fixtures.Options.order

    def config(self):
        c = fixtures.Options.config(self)
        c["groups"][0]["type"] = "sizes"
        c["groups"][0]["choices"][0]["max_flavors"] = 1
        c["groups"][0]["choices"][1]["max_flavors"] = 6
        c["groups"][0]["choices"][2]["max_flavors"] = 1
        c["groups"].append(
            {
                "id": "flavors",
                "title": "Sabores",
                "type": "flavors",
                "required": True,
                "enabled": True,
                "max": 20,
                "choices": [
                    {"id": f"f{i}", "label": name, "price": price, "enabled": True}
                    for i, (name, price) in enumerate(
                        [
                            ("Margherita", 5000),
                            ("Calabresa", 6000),
                            ("Frango", 7000),
                            ("Portuguesa", 8000),
                            ("Chocolate", 9000),
                            ("Queijos", 10000),
                        ]
                    )
                ],
            }
        )
        return c

    def item(self, count=4):
        return {
            "id": 1,
            "quantidade": 2,
            "opcoes_versao": public_product(db.session.get(Produto, 1))["version"],
            "quantidade_sabores": count,
            "opcoes": {
                "size": ["large"],
                "border": ["cheese"],
                "flavors": [f"f{i}" for i in range(count)],
            },
            "observacao": "Sem cebola",
            "preco": 1,
        }

    def test_average_replaces_base_size_and_border_added_once(self):
        self.save()
        r = self.order(self.item())
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        p = db.session.get(Pedido, r.json["id"])
        self.assertEqual(p.itens[0].preco, 8500)
        self.assertEqual(p.total, 17000)
        self.assertIn("Sabores (4):", p.itens[0].observacao)

    def test_family_six_flavors_and_one_flavor(self):
        self.save()
        r = self.order(self.item(6))
        self.assertEqual(r.status_code, 201)
        p = db.session.get(Pedido, r.json["id"])
        self.assertEqual(p.itens[0].preco, 9500)
        i = self.item(1)
        i["opcoes"]["size"] = ["small"]
        i["opcoes"]["border"] = []
        self.assertEqual(self.order(i).status_code, 200)

    def test_wrong_count_duplicate_hidden_and_size_limit(self):
        self.save()
        for change in [
            "less",
            "more",
            "duplicate",
            "size",
            "missing",
            "bool",
            "hidden",
        ]:
            i = self.item()
            if change == "less":
                i["opcoes"]["flavors"].pop()
            if change == "more":
                i["opcoes"]["flavors"].append("f4")
            if change == "duplicate":
                i["opcoes"]["flavors"] = ["f0"] * 4
            if change == "size":
                i["opcoes"]["size"] = ["small"]
            if change == "missing":
                i.pop("quantidade_sabores")
            if change == "bool":
                i["quantidade_sabores"] = True
            if change == "hidden":
                i["opcoes"]["flavors"][0] = "inventado"
            self.assertEqual(self.order(i).status_code, 400, change)
        self.assertEqual(db.session.scalar(db.select(db.func.count(Pedido.id))), 0)

    def test_rounding_half_cent_up_and_history(self):
        c = self.config()
        c["groups"][-1]["choices"][0]["price"] = 5000
        c["groups"][-1]["choices"][1]["price"] = 5001
        self.save(c)
        i = self.item(2)
        i["opcoes"]["border"] = []
        r = self.order(i)
        self.assertEqual(r.status_code, 201)
        p = db.session.get(Pedido, r.json["id"])
        self.assertEqual(p.itens[0].preco, 6501)
        c = self.config()
        c["groups"][-1]["choices"][0]["price"] = 9999
        self.save(c)
        db.session.refresh(p)
        self.assertEqual(p.itens[0].preco, 6501)

    def test_pair_and_limits_validated(self):
        c = self.config()
        c["groups"][0]["choices"][0]["max_flavors"] = 0
        self.assertEqual(self.post("/cadastros/produtos/1/opcoes", c).status_code, 400)
        c = self.config()
        c["groups"].pop()
        self.assertEqual(self.post("/cadastros/produtos/1/opcoes", c).status_code, 400)
        c = self.config()
        c["groups"].append(dict(c["groups"][-1], id="outros"))
        self.assertEqual(self.post("/cadastros/produtos/1/opcoes", c).status_code, 400)
