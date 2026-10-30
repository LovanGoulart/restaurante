"""Nome e mesa obrigatórios no início do atendimento pelo QR Code."""

import unittest
import test_new_accesses as fixtures
from models import db, Usuario
from werkzeug.security import generate_password_hash


class MesaQR(unittest.TestCase):
    setUp = fixtures.Accesses.setUp
    tearDown = fixtures.Accesses.tearDown
    create = fixtures.Accesses.create
    prepare = fixtures.Accesses.prepare
    csrf_for = fixtures.Accesses.csrf_for
    api = fixtures.Accesses.api
    order = fixtures.Accesses.order
    waiter = fixtures.Accesses.waiter

    def enter(self, client, nome="João", mesa="008"):
        token = self.csrf_for(client, "/r/loja-um/salao")
        return client.post(
            "/r/loja-um/salao", data={"csrf": token, "nome": nome, "numero_mesa": mesa}
        )

    def test_required_fields_and_invalid_data_preserve_form(self):
        site, app = self.prepare()
        c = self.app.test_client()
        html = c.get("/r/loja-um/salao").get_data(as_text=True)
        self.assertIn('name="numero_mesa"', html)
        for name, table in [
            ("", "8"),
            ("Pessoa", ""),
            ("Pessoa", "abc"),
            ("Pessoa", "0"),
            ("Pessoa", "-1"),
            ("Pessoa", "1.5"),
            ("Pessoa", "1" * 13),
        ]:
            response = self.enter(c, name, table)
            self.assertEqual(response.status_code, 400)
            self.assertIn('role="alert"', response.get_data(as_text=True))
        with app.app_context():
            self.assertEqual(
                db.session.scalar(db.select(db.func.count()).select_from(Usuario)), 3
            )

    def test_table_reaches_order_waiter_kitchen_and_notification(self):
        site, app = self.prepare()
        c = self.app.test_client()
        self.assertEqual(self.enter(c).status_code, 302)
        page = c.get("/r/loja-um/salao/cardapio").get_data(as_text=True)
        self.assertIn("Mesa 8", page)
        result = self.api(
            c,
            "/api/salao/pedidos",
            {
                "chave": "table-order-key-12345",
                "numero_mesa": "99",
                "itens": [{"id": 1, "quantidade": 1}],
            },
        )
        self.assertEqual(result.status_code, 201)
        order = c.get("/r/loja-um/api/salao/pedidos").json[0]
        self.assertEqual(order["numero_mesa"], "8")
        self.assertEqual(order["comanda"], "")
        self.assertTrue(order["aguardando_comanda"])
        w = self.waiter()
        p = next(
            p for p in w.get("/r/loja-um/api/pedidos").json if p["id"] == order["id"]
        )
        self.assertEqual(p["numero_mesa"], "8")
        notices = w.get("/r/loja-um/api/notificacoes").json["items"]
        # Garçom recebe aviso de pronto pelo fluxo normal; cozinha recebe o novo pedido.
        with app.app_context():
            from models import Notificacao

            messages = db.session.scalars(db.select(Notificacao.mensagem)).all()
            self.assertTrue(any("Mesa 8" in m for m in messages))
        self.assertEqual(
            self.api(
                w,
                f"/api/pedidos/{order['id']}/comanda",
                {"comanda": "15", "numero_mesa": "8"},
            ).status_code,
            200,
        )
        self.assertEqual(c.get("/r/loja-um/api/salao/pedidos").json[0]["comanda"], "15")

    def test_edit_keeps_identity_and_old_order_table(self):
        self.prepare()
        c = self.app.test_client()
        self.enter(c)
        first = self.order(c)
        token = self.csrf_for(c, "/r/loja-um/salao?editar=1")
        r = c.post(
            "/r/loja-um/salao",
            data={"csrf": token, "nome": "João Silva", "numero_mesa": "12"},
        )
        self.assertEqual(r.status_code, 302)
        second = self.order(c, key="second-table-order-key")
        orders = {p["id"]: p for p in c.get("/r/loja-um/api/salao/pedidos").json}
        self.assertEqual(orders[first]["numero_mesa"], "8")
        self.assertEqual(orders[second]["numero_mesa"], "12")
        self.assertEqual(len(orders), 2)

    def test_existing_guest_without_table_is_redirected_and_keeps_orders(self):
        site, app = self.prepare()
        direct = app.test_client()
        with app.app_context():
            user = Usuario(
                nome="Sessão antiga",
                login="old-guest",
                senha=generate_password_hash("unused-password"),
                perfil="visitante",
            )
            db.session.add(user)
            db.session.commit()
            uid = user.id
        with direct.session_transaction() as session:
            session["uid"] = uid
            session["csrf"] = "legacy-csrf"
        self.assertEqual(direct.get("/salao/cardapio").status_code, 302)
        response = direct.post(
            "/api/salao/pedidos",
            json={
                "chave": "legacy-missing-table-key",
                "itens": [{"id": 1, "quantidade": 1}],
            },
            headers={"X-CSRF-Token": "legacy-csrf"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            direct.post(
                "/salao",
                data={
                    "csrf": "legacy-csrf",
                    "nome": "Sessão antiga",
                    "numero_mesa": "7",
                },
            ).status_code,
            302,
        )
        with direct.session_transaction() as session:
            self.assertEqual(session["uid"], uid)


if __name__ == "__main__":
    unittest.main()
