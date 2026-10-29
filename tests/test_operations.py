import unittest
from datetime import datetime, timedelta, timezone
import test_couriers
from models import db, Pedido, Entrega, Usuario, Movimento


class Operations(unittest.TestCase):
    setUp = test_couriers.Couriers.setUp
    tearDown = test_couriers.Couriers.tearDown
    order = test_couriers.Couriers.order
    login = test_couriers.Couriers.login
    post = test_couriers.Couriers.post
    assign = test_couriers.Couriers.assign
    complete = test_couriers.Couriers.complete
    cash = test_couriers.Couriers.cash

    def test_details_permissions_and_old_kitchen_order(self):
        self.login("cozinha")
        self.assertNotIn(
            self.delivery.id, [p["id"] for p in self.client.get("/api/pedidos").json]
        )
        self.assertEqual(
            self.client.get(f"/api/pedidos/{self.delivery.id}/detalhes").status_code,
            200,
        )
        self.login("garcom")
        self.assertEqual(
            self.client.get(f"/api/pedidos/{self.delivery.id}/detalhes").status_code,
            403,
        )
        self.assertEqual(
            self.client.get(f"/api/pedidos/{self.salon.id}/detalhes").status_code, 200
        )
        self.login("cliente")
        self.assertEqual(
            self.client.get(f"/api/pedidos/{self.delivery.id}/detalhes").status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/api/pedidos/{self.salon.id}/detalhes").status_code, 403
        )
        db.session.add(
            Usuario(nome="Outro cliente", login="other", senha="x", perfil="cliente")
        )
        db.session.commit()
        other = db.session.scalar(db.select(Usuario).where(Usuario.login == "other"))
        with self.client.session_transaction() as session:
            session["uid"] = other.id
        self.assertEqual(
            self.client.get(f"/api/pedidos/{self.delivery.id}/detalhes").status_code,
            403,
        )

    def test_waiter_completed_paid_last(self):
        self.salon.status = "entregue"
        self.salon.pago = True
        paid_id = self.salon.id
        for status in ["aberto", "em_preparo", "pronto", "entregue"]:
            db.session.add(
                Pedido(
                    mesa="01", usuario_id=self.ids["garcom"], status=status, pago=False
                )
            )
        db.session.commit()
        self.login("garcom")
        rows = self.client.get("/api/pedidos").json
        self.assertEqual(rows[-1]["id"], paid_id)
        self.assertEqual(
            [p["status"] for p in rows[:-1]],
            ["pronto", "em_preparo", "aberto", "entregue"],
        )

    def test_explicit_confirmation_required(self):
        e = self.assign()
        self.login("driver1")
        self.assertEqual(
            self.post(
                f"/api/entregas/{e.id}/concluir",
                {"confirmado": False, "forma_pagamento": "dinheiro"},
            ).status_code,
            400,
        )
        self.assertIsNone(db.session.get(Entrega, e.id).entregue_em)
        self.complete(e)
        self.login("admin")
        self.cash()
        before = db.session.scalar(db.select(db.func.count()).select_from(Movimento))
        self.assertEqual(
            self.post(
                "/api/acerto-entregadores", {"entregas": [e.id], "confirmado": False}
            ).status_code,
            400,
        )
        self.assertEqual(
            before, db.session.scalar(db.select(db.func.count()).select_from(Movimento))
        )
        self.assertIsNone(db.session.get(Entrega, e.id).acertado_em)

    def test_old_delivery_notification_still_scoped(self):
        e = self.assign()
        self.complete(e)
        e.entregue_em = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=5
        )
        db.session.commit()
        self.login("driver1")
        self.assertNotIn(
            self.delivery.id,
            [p["id"] for p in self.client.get("/api/entregas").json["items"]],
        )
        self.assertIn(
            self.delivery.id,
            [
                p["id"]
                for p in self.client.get(
                    f"/api/entregas?pedido={self.delivery.id}"
                ).json["items"]
            ],
        )
        self.login("driver2")
        self.assertEqual(
            self.client.get(f"/api/entregas?pedido={self.delivery.id}").json["items"],
            [],
        )

    def test_desktop_logout_for_every_role(self):
        for name, path in [
            ("admin", "/pedidos"),
            ("garcom", "/pdv"),
            ("cozinha", "/pedidos"),
            ("cliente", "/cardapio"),
            ("driver1", "/entregas"),
        ]:
            self.login(name)
            self.assertIn(b'class="desktop-logout"', self.client.get(path).data)
            with self.client.session_transaction() as session:
                csrf = session["csrf"]
            self.assertEqual(
                self.client.post("/logout", data={"csrf": csrf}).status_code, 302
            )
            with self.client.session_transaction() as session:
                self.assertNotIn("uid", session)
