"""Controle parcial, concorrência e permissões do checklist por item."""

import unittest
import test_new_accesses as fixtures
from models import db, Pedido, PedidoOnline, Cliente, Usuario, Item, Notificacao
from datetime import date


class ItemChecklist(unittest.TestCase):
    setUp = fixtures.Accesses.setUp
    tearDown = fixtures.Accesses.tearDown
    create = fixtures.Accesses.create
    prepare = fixtures.Accesses.prepare
    csrf_for = fixtures.Accesses.csrf_for
    api = fixtures.Accesses.api
    waiter = fixtures.Accesses.waiter
    tenant_login = fixtures.Accesses.tenant_login

    def setup_order(self, paid=False):
        site, app = self.prepare()
        waiter = self.waiter()
        response = self.api(
            waiter,
            "/api/pedidos",
            {
                "comanda": "45",
                "numero_mesa": "8",
                "itens": [
                    {"id": 1, "quantidade": 1, "observacao": "Comida"},
                    {"id": 1, "quantidade": 1, "observacao": "Bebida"},
                ],
            },
        )
        self.assertEqual(response.status_code, 201)
        id = response.json["id"]
        p = waiter.get(f"/r/loja-um/api/pedidos/{id}/detalhes").json
        kitchen = self.app.test_client()
        token = self.csrf_for(kitchen)
        self.assertEqual(
            kitchen.post(
                "/r/loja-um/login",
                data={"csrf": token, "login": "cozinha", "senha": "test-password"},
            ).status_code,
            302,
        )
        if paid:
            with app.app_context():
                db.session.get(Pedido, id).pago = True
                db.session.commit()
        return app, waiter, kitchen, p

    def check(self, c, p, i, acao, marked=True, expected="aberto"):
        return self.api(
            c,
            f"/api/pedidos/{p['id']}/itens/{p['itens'][i]['id']}/checklist",
            {"acao": acao, "marcado": marked, "etapa_anterior": expected},
        )

    def test_drink_served_while_food_preparing(self):
        app, w, k, p = self.setup_order()
        self.api(k, f"/api/pedidos/{p['id']}/status", {"status": "em_preparo"})
        r = self.check(w, p, 1, "entregue", expected="em_preparo")
        self.assertEqual(r.status_code, 200)
        result = r.json["pedido"]
        self.assertEqual(result["status"], "em_preparo")
        self.assertEqual(
            [i["etapa"] for i in result["itens"]], ["em_preparo", "entregue"]
        )
        self.assertEqual(result["total"], p["total"])
        r = self.check(k, p, 0, "pronto", expected="em_preparo")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["pedido"]["status"], "pronto")
        self.assertEqual(
            self.check(w, p, 0, "entregue", expected="pronto").json["pedido"]["status"],
            "entregue",
        )

    def test_partial_ready_alert_to_waiter_and_persistent(self):
        app, w, k, p = self.setup_order()
        r = self.check(k, p, 0, "pronto")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["pedido"]["status"], "em_preparo")
        inbox = w.get("/r/loja-um/api/notificacoes").json["items"]
        self.assertTrue(
            any(n["tipo"] == "item_pronto" and "Mesa 8" in n["mensagem"] for n in inbox)
        )
        self.assertEqual(
            w.get(f"/r/loja-um/api/pedidos/{p['id']}/detalhes").json["itens"][0][
                "etapa"
            ],
            "pronto",
        )
        self.assertIn(p["id"], [x["id"] for x in k.get("/r/loja-um/api/pedidos").json])
        result = self.check(k, p, 1, "pronto").json["pedido"]
        self.assertEqual(result["status"], "pronto")
        self.assertNotIn(
            p["id"], [x["id"] for x in k.get("/r/loja-um/api/pedidos").json]
        )

    def test_roles_cannot_apply_other_check(self):
        app, w, k, p = self.setup_order()
        self.assertEqual(self.check(k, p, 0, "entregue").status_code, 403)
        self.assertEqual(self.check(w, p, 0, "pronto").status_code, 403)
        c = self.app.test_client()
        self.assertEqual(self.check(c, p, 0, "pronto").status_code, 401)
        self.assertEqual(
            w.post(
                f"/r/loja-um/api/pedidos/{p['id']}/itens/{p['itens'][0]['id']}/checklist",
                json={"acao": "entregue", "marcado": True, "etapa_anterior": "aberto"},
            ).status_code,
            400,
        )

    def test_undo_and_kitchen_cannot_undo_delivered(self):
        app, w, k, p = self.setup_order()
        self.check(k, p, 0, "pronto")
        self.assertEqual(
            self.check(k, p, 0, "pronto", False, "pronto").json["pedido"]["itens"][0][
                "etapa"
            ],
            "em_preparo",
        )
        self.check(w, p, 1, "entregue")
        self.assertEqual(
            self.check(k, p, 1, "pronto", False, "entregue").status_code, 409
        )
        self.assertEqual(
            self.check(w, p, 1, "entregue", False, "entregue").json["pedido"]["itens"][
                1
            ]["etapa"],
            "pronto",
        )

    def test_stale_conflict_and_repeat_is_idempotent(self):
        app, w, k, p = self.setup_order()
        self.check(k, p, 0, "pronto")
        before = len(w.get("/r/loja-um/api/notificacoes").json["items"])
        self.assertFalse(self.check(k, p, 0, "pronto").json["alterado"])
        self.assertEqual(
            len(w.get("/r/loja-um/api/notificacoes").json["items"]), before
        )
        self.assertEqual(
            self.check(w, p, 0, "entregue", expected="aberto").status_code, 409
        )
        self.assertEqual(
            self.check(w, p, 0, "entregue", expected="pronto").status_code, 200
        )

    def test_item_other_order_cannot_be_changed(self):
        app, w, k, p = self.setup_order()
        other = self.api(
            w,
            "/api/pedidos",
            {
                "comanda": "46",
                "numero_mesa": "9",
                "itens": [{"id": 1, "quantidade": 1}],
            },
        ).json["id"]
        self.assertEqual(
            self.api(
                w,
                f"/api/pedidos/{other}/itens/{p['itens'][0]['id']}/checklist",
                {"acao": "entregue", "marcado": True, "etapa_anterior": "aberto"},
            ).status_code,
            404,
        )

    def test_paid_pending_can_be_served_but_finalized_cannot_reopen(self):
        app, w, k, p = self.setup_order(paid=True)
        self.assertEqual(self.check(w, p, 0, "entregue").status_code, 200)
        r = self.check(w, p, 1, "entregue")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["pedido"]["status"], "entregue")
        self.assertEqual(
            self.check(w, p, 0, "entregue", False, "entregue").status_code, 409
        )

    def test_global_ready_preserves_delivered_and_marks_other_pending(self):
        app, w, k, p = self.setup_order()
        self.check(w, p, 1, "entregue")
        r = self.api(k, f"/api/pedidos/{p['id']}/status", {"status": "pronto"})
        self.assertEqual(r.status_code, 200)
        items = w.get(f"/r/loja-um/api/pedidos/{p['id']}/detalhes").json["itens"]
        self.assertEqual([i["etapa"] for i in items], ["pronto", "entregue"])

    def test_waiter_online_and_courier_flow_remain_restricted(self):
        app, w, k, p = self.setup_order()
        with app.app_context():
            client_user = Usuario(
                nome="Cliente", login="client", senha="unused", perfil="cliente"
            )
            db.session.add(client_user)
            db.session.flush()
            c = Cliente(
                usuario_id=client_user.id,
                cpf_cifrado="test",
                cpf_hash="test",
                cpf_final="00",
                nascimento=date(1990, 1, 1),
            )
            db.session.add(c)
            db.session.flush()
            order = db.session.get(Pedido, p["id"])
            order.online = PedidoOnline(
                cliente_id=c.id,
                modalidade="entrega",
                destinatario="Cliente",
                forma_pagamento="pix",
                taxa_entrega=0,
            )
            db.session.commit()
        self.assertEqual(self.check(w, p, 0, "entregue").status_code, 403)
        self.assertEqual(self.check(k, p, 0, "pronto").status_code, 200)
        with app.app_context():
            db.session.get(Pedido, p["id"]).status = "saiu_entrega"
            db.session.commit()
        self.assertEqual(self.check(k, p, 1, "pronto").status_code, 409)

    def test_invalid_payload_is_rejected(self):
        app, w, k, p = self.setup_order()
        self.assertEqual(
            self.api(
                k,
                f"/api/pedidos/{p['id']}/itens/{p['itens'][0]['id']}/checklist",
                {"acao": "pronto", "marcado": "true", "etapa_anterior": "aberto"},
            ).status_code,
            400,
        )

    def test_merged_qr_customers_receive_only_their_item_alerts(self):
        app, w, k, p = self.setup_order()
        guest = fixtures.Accesses.guest
        a = guest(self, "A")
        b = guest(self, "B")
        data = {
            "chave": "private-qr-items-12345",
            "itens": [{"id": 1, "quantidade": 1}, {"id": 1, "quantidade": 1}],
        }
        for client in [a, b]:
            response = self.api(client, "/api/salao/pedidos", data)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(
                self.api(
                    w,
                    f"/api/pedidos/{response.json['id']}/comanda",
                    {"comanda": "45", "numero_mesa": "8"},
                ).status_code,
                200,
            )
        self.assertEqual(self.check(k, p, 0, "pronto").status_code, 200)
        for client in [a, b]:
            self.assertFalse(
                any(
                    n["tipo"] == "item_pronto"
                    for n in client.get("/r/loja-um/api/notificacoes").json["items"]
                )
            )
        own = a.get("/r/loja-um/api/salao/pedidos").json[0]
        item_id = own["itens"][0]["id"]
        self.assertEqual(
            self.api(
                k,
                f"/api/pedidos/{p['id']}/itens/{item_id}/checklist",
                {"acao": "pronto", "marcado": True, "etapa_anterior": "aberto"},
            ).status_code,
            200,
        )
        self.assertTrue(
            any(
                n["tipo"] == "item_pronto"
                for n in a.get("/r/loja-um/api/notificacoes").json["items"]
            )
        )
        self.assertFalse(
            any(
                n["tipo"] == "item_pronto"
                for n in b.get("/r/loja-um/api/notificacoes").json["items"]
            )
        )


if __name__ == "__main__":
    unittest.main()
