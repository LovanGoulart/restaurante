import unittest
import tempfile
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
from app import create_app
from models import (
    db,
    Usuario,
    Cliente,
    Categoria,
    Produto,
    Pedido,
    PedidoOnline,
    Item,
    Entrega,
    Caixa,
    Movimento,
    Notificacao,
)
from werkzeug.security import generate_password_hash
from couriers import day_range
from migrate import migrate


class Couriers(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "SECRET_KEY": "test",
                "SSE_DURATION": 0.02,
                "SSE_INTERVAL": 0.005,
            }
        )
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        for role, name in [
            ("admin", "admin"),
            ("garcom", "garcom"),
            ("cozinha", "cozinha"),
            ("cliente", "cliente"),
            ("entregador", "driver1"),
            ("entregador", "driver2"),
        ]:
            db.session.add(
                Usuario(
                    nome=name,
                    login="admin@example.com" if role == "admin" else name,
                    perfil=role,
                    senha=generate_password_hash("test-password"),
                    ativo=True,
                )
            )
        db.session.flush()
        self.ids = {u.nome: u.id for u in db.session.scalars(db.select(Usuario))}
        self.customer = Cliente(
            usuario_id=self.ids["cliente"],
            cpf_cifrado="fixture",
            cpf_hash="fixture",
            cpf_final="00",
            nascimento=date(1990, 1, 1),
        )
        db.session.add(self.customer)
        db.session.flush()
        self.delivery = self.order()
        self.pickup = self.order("retirada")
        self.salon = Pedido(mesa="08", usuario_id=self.ids["garcom"], status="pronto")
        self.salon.itens.append(Item(nome="Prato salão", preco=1000, quantidade=1))
        db.session.add(self.salon)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def order(self, mode="entrega", price=2500):
        p = Pedido(mesa="Online", usuario_id=self.ids["cliente"], status="pronto")
        p.itens.append(Item(nome="Prato teste", preco=price, quantidade=1))
        p.online = PedidoOnline(
            cliente_id=self.customer.id,
            modalidade=mode,
            destinatario="Cliente teste",
            endereco="Rua teste",
            bairro="Centro",
            numero="123",
            referencia="Referência teste",
            forma_pagamento="pix",
            taxa_entrega=500 if mode == "entrega" else 0,
        )
        db.session.add(p)
        db.session.flush()
        return p

    def login(self, name):
        self.client.get("/login")
        with self.client.session_transaction() as s:
            token = s["csrf"]
        r = self.client.post(
            "/login",
            data={
                "csrf": token,
                "login": "admin@example.com" if name == "admin" else name,
                "senha": "test-password",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.client.get("/")

        if name == "admin":
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

    def post(self, path, data):
        with self.client.session_transaction() as s:
            token = s["csrf"]
        return self.client.post(path, json=data, headers={"X-CSRF-Token": token})

    def assign(self, p=None, driver="driver1"):
        self.login("admin")
        p = p or self.delivery
        r = self.post(
            f"/api/pedidos/{p.id}/entregador", {"entregador_id": self.ids[driver]}
        )
        self.assertEqual(r.status_code, 200)
        return db.session.scalar(db.select(Entrega).where(Entrega.pedido_id == p.id))

    def complete(self, e=None, form="dinheiro", driver="driver1"):
        e = e or self.assign()
        self.login(driver)
        r = self.post(
            f"/api/entregas/{e.id}/concluir",
            {"forma_pagamento": form, "confirmado": True},
        )
        self.assertEqual(r.status_code, 200)
        return e

    def cash(self):
        db.session.add(Caixa(inicial=10000))
        db.session.commit()

    def test_admin_creates_driver_and_role_is_restricted(self):
        self.login("admin")
        with self.client.session_transaction() as s:
            token = s["csrf"]
        r = self.client.post(
            "/cadastros/usuarios",
            data={
                "csrf": token,
                "nome": "Novo entregador",
                "login": "novo-driver",
                "perfil": "entregador",
                "senha": "test-password",
                "ativo": "on",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            db.session.scalar(
                db.select(Usuario).where(Usuario.login == "novo-driver")
            ).perfil,
            "entregador",
        )
        self.login("driver1")
        self.assertEqual(self.client.get("/").location, "/entregas")
        self.assertEqual(self.client.get("/entregas").status_code, 200)
        html = self.client.get("/entregas").get_data(as_text=True)
        self.assertNotIn('href="/pdv"', html)
        self.assertNotIn('href="/caixa"', html)
        for path in [
            "/pdv",
            "/pedidos",
            "/api/pedidos",
            "/dashboard",
            "/caixa",
            "/cadastros/usuarios",
            "/clientes",
            "/loja",
            "/minha-conta",
            "/meus-pedidos",
            "/api/entregadores",
            "/acerto-entregadores",
            "/api/acerto-entregadores",
        ]:
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_assignment_only_admin_delivery_and_ready(self):
        self.login("garcom")
        self.assertEqual(
            self.post(
                f"/api/pedidos/{self.delivery.id}/entregador",
                {"entregador_id": self.ids["driver1"]},
            ).status_code,
            403,
        )
        self.login("admin")
        for p in [self.pickup, self.salon]:
            self.assertEqual(
                self.post(
                    f"/api/pedidos/{p.id}/entregador",
                    {"entregador_id": self.ids["driver1"]},
                ).status_code,
                400,
            )
        self.assertEqual(
            self.post(
                f"/api/pedidos/{self.delivery.id}/entregador",
                {"entregador_id": self.ids["garcom"]},
            ).status_code,
            400,
        )
        self.delivery.status = "aberto"
        db.session.commit()
        self.assertEqual(
            self.post(
                f"/api/pedidos/{self.delivery.id}/entregador",
                {"entregador_id": self.ids["driver1"]},
            ).status_code,
            409,
        )

    def test_own_assignments_and_customer_data_minimization(self):
        e = self.assign()
        self.assertEqual(self.delivery.status, "saiu_entrega")
        self.login("driver1")
        rows = self.client.get("/api/entregas").json["items"]
        self.assertEqual([r["id"] for r in rows], [self.delivery.id])
        self.assertIn("endereco", rows[0])
        self.assertNotIn("cpf", str(rows))
        self.assertNotIn("nascimento", str(rows))
        self.login("driver2")
        self.assertEqual(self.client.get("/api/entregas").json["items"], [])
        self.assertEqual(
            self.post(
                f"/api/entregas/{e.id}/concluir",
                {"forma_pagamento": "pix", "confirmado": True},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.post(
                f"/api/pedidos/{self.delivery.id}/pagar", {"forma": "pix"}
            ).status_code,
            403,
        )

    def test_delivery_records_actual_form_without_cash_posting(self):
        e = self.complete(form="dinheiro")
        self.assertEqual(self.delivery.status, "entregue")
        self.assertFalse(self.delivery.pago)
        self.assertEqual(e.valor_recebido, 3000)
        self.assertEqual(e.forma_pagamento, "dinheiro")
        self.assertIsNotNone(e.entregue_em)
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(Movimento)), 0
        )
        self.assertEqual(
            self.post(
                f"/api/entregas/{e.id}/concluir",
                {"forma_pagamento": "pix", "confirmado": True},
            ).status_code,
            409,
        )

    def test_payment_validation_and_duplicate_receipt_guards(self):
        e = self.assign()
        self.login("driver1")
        self.assertEqual(
            self.post(
                f"/api/entregas/{e.id}/concluir", {"forma_pagamento": "dinheiro"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post(
                f"/api/entregas/{e.id}/concluir",
                {"forma_pagamento": "invalid", "confirmado": True},
            ).status_code,
            400,
        )
        self.login("admin")
        self.assertEqual(
            self.post(
                f"/api/pedidos/{self.delivery.id}/status", {"status": "entregue"}
            ).status_code,
            409,
        )
        e = self.complete(e)
        self.cash()
        self.login("admin")
        self.assertEqual(
            self.post(
                f"/api/pedidos/{self.delivery.id}/pagar", {"forma": "dinheiro"}
            ).status_code,
            409,
        )

    def test_cash_settlement_requires_cashbox_and_is_atomic_once(self):
        e = self.complete()
        self.login("admin")
        body = {"entregas": [e.id], "confirmado": True}
        self.assertEqual(self.post("/api/acerto-entregadores", body).status_code, 409)
        self.assertFalse(self.delivery.pago)
        self.assertIsNone(e.acertado_em)
        self.cash()
        self.assertEqual(self.post("/api/acerto-entregadores", body).status_code, 200)
        self.assertTrue(self.delivery.pago)
        self.assertIsNotNone(e.acertado_em)
        move = db.session.scalar(db.select(Movimento))
        self.assertEqual(move.valor, 3000)
        self.assertEqual(move.forma, "dinheiro")
        self.assertEqual(move.pedido_id, self.delivery.id)
        self.assertEqual(self.post("/api/acerto-entregadores", body).status_code, 409)
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(Movimento)), 1
        )

    def test_prepaid_delivery_is_not_charged_or_counted_twice(self):
        self.cash()
        self.login("admin")
        self.assertEqual(
            self.post(
                f"/api/pedidos/{self.delivery.id}/pagar", {"forma": "pix"}
            ).status_code,
            200,
        )
        e = self.assign()
        self.complete(e, form="dinheiro")
        self.assertTrue(e.pago_antecipado)
        self.assertEqual(e.forma_pagamento, "pix")
        self.assertEqual(e.valor_recebido, 0)
        self.login("admin")
        summary = self.client.get("/api/acerto-entregadores").json["resumo"][0]
        self.assertEqual(summary["antecipado"], 3000)
        self.assertEqual(summary["dinheiro_repassar"], 0)
        self.assertEqual(
            self.post(
                "/api/acerto-entregadores", {"entregas": [e.id], "confirmado": True}
            ).status_code,
            200,
        )
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(Movimento)), 1
        )

    def test_summary_by_driver_day_and_payment_method(self):
        e1 = self.complete(form="dinheiro")
        p2 = self.order(price=4500)
        db.session.commit()
        e2 = self.complete(self.assign(p2), form="pix")
        p3 = self.order(price=1500)
        db.session.commit()
        e3 = self.complete(self.assign(p3, "driver2"), form="credito", driver="driver2")
        self.login("admin")
        data = self.client.get("/api/acerto-entregadores").json
        self.assertEqual(len(data["resumo"]), 2)
        r = next(r for r in data["resumo"] if r["id"] == self.ids["driver1"])
        self.assertEqual(r["total_pedidos"], 8000)
        self.assertEqual(r["a_conferir"], 8000)
        self.assertEqual(r["dinheiro_repassar"], 3000)
        self.assertEqual(r["formas"]["pix"], 5000)
        filtered = self.client.get(
            "/api/acerto-entregadores?entregador_id=" + str(self.ids["driver2"])
        ).json
        self.assertEqual(len(filtered["items"]), 1)
        self.assertEqual(filtered["resumo"][0]["formas"]["credito"], 2000)

    def test_reassignment_and_courier_deactivation_guard(self):
        e = self.assign()
        self.login("admin")
        with self.client.session_transaction() as s:
            token = s["csrf"]
        r = self.client.post(
            "/cadastros/usuarios",
            data={
                "csrf": token,
                "id": self.ids["driver1"],
                "nome": "driver1",
                "login": "driver1",
                "perfil": "entregador",
                "senha": "",
            },
        )
        self.assertEqual(r.status_code, 409)
        self.assign(driver="driver2")
        self.assertEqual(e.entregador_id, self.ids["driver2"])
        self.login("driver1")
        self.assertEqual(self.client.get("/api/entregas").json["items"], [])
        self.assertEqual(
            self.post(
                f"/api/entregas/{e.id}/concluir",
                {"forma_pagamento": "dinheiro", "confirmado": True},
            ).status_code,
            403,
        )

    def test_notifications_are_scoped_to_assigned_driver(self):
        e = self.assign()
        self.login("driver1")
        notifications = self.client.get("/api/notificacoes").json["items"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(
            notifications[0]["url"], f"/entregas?pedido={self.delivery.id}"
        )
        self.login("driver2")
        self.assertEqual(self.client.get("/api/notificacoes").json["items"], [])
        self.assign(driver="driver2")
        self.login("driver2")
        self.assertTrue(
            any(
                n["tipo"] == "atribuida"
                for n in self.client.get("/api/notificacoes").json["items"]
            )
        )

    def test_partial_invalid_settlement_rolls_back_all(self):
        e1 = self.complete()
        p2 = self.order()
        db.session.commit()
        e2 = self.complete(self.assign(p2))
        self.cash()
        self.login("admin")
        self.assertEqual(
            self.post(
                "/api/acerto-entregadores",
                {"entregas": [e1.id, e2.id + 1000], "confirmado": True},
            ).status_code,
            409,
        )
        self.assertFalse(self.delivery.pago)
        self.assertIsNone(e1.acertado_em)
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(Movimento)), 0
        )

    def test_zero_value_delivery_can_be_settled(self):
        p = self.order(price=0)
        p.online.taxa_entrega = 0
        db.session.commit()
        e = self.complete(self.assign(p), form="dinheiro")
        self.assertEqual(e.valor_recebido, 0)
        self.cash()
        self.login("admin")
        self.assertEqual(
            self.post(
                "/api/acerto-entregadores", {"entregas": [e.id], "confirmado": True}
            ).status_code,
            200,
        )
        self.assertTrue(p.pago)
        self.assertEqual(
            db.session.scalar(
                db.select(Movimento).where(Movimento.pedido_id == p.id)
            ).valor,
            0,
        )

    def test_day_boundary_is_brazilian_local_day(self):
        e = self.complete()
        e.entregue_em = datetime(2026, 10, 28, 2, 59, tzinfo=timezone.utc)
        db.session.commit()
        self.login("admin")
        self.assertEqual(
            len(
                self.client.get("/api/acerto-entregadores?data=2026-10-27").json[
                    "items"
                ]
            ),
            1,
        )
        self.assertEqual(
            len(
                self.client.get("/api/acerto-entregadores?data=2026-10-28").json[
                    "items"
                ]
            ),
            0,
        )


class CourierMigration(unittest.TestCase):
    def test_migrate_v31_keeps_orders_and_payments(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "old.db"
            app = create_app(
                {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(path)}
            )
            with app.app_context():
                db.metadata.create_all(
                    db.engine,
                    tables=[
                        t for t in db.metadata.sorted_tables if t.name != "entrega"
                    ],
                )
                u = Usuario(
                    nome="Admin antigo",
                    login="admin",
                    senha="preservar",
                    perfil="admin",
                )
                db.session.add(u)
                db.session.flush()
                p = Pedido(mesa="08", usuario_id=u.id, pago=True)
                p.itens.append(Item(nome="Produto antigo", preco=2000, quantidade=1))
                db.session.add(p)
                cash = Caixa(inicial=10000)
                db.session.add(cash)
                db.session.flush()
                db.session.add(
                    Movimento(
                        pedido_id=p.id,
                        caixa_id=cash.id,
                        tipo="recebimento",
                        forma="pix",
                        valor=2000,
                    )
                )
                db.session.commit()
                backup = migrate()
                self.assertTrue(backup.is_file())
                self.assertEqual(db.session.get(Pedido, p.id).total, 2000)
                self.assertTrue(db.session.get(Pedido, p.id).pago)
                self.assertEqual(db.session.scalar(db.select(Movimento)).valor, 2000)
                self.assertIsNone(migrate())
                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
