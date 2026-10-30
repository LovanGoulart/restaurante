"""Regressões de cadastro, acesso por e-mail, comandas e privacidade QR."""

import sqlite3
import threading
import time
from pathlib import Path
from werkzeug.security import generate_password_hash
import unittest
from app import create_app
from models import (
    db,
    Usuario,
    Pedido,
    Categoria,
    Produto,
)
import test_platform
from test_platform import csrf
from atualizar_sistema import migrate_current


class Accesses(unittest.TestCase):
    setUp = test_platform.Platform.setUp
    tearDown = test_platform.Platform.tearDown
    create = test_platform.Platform.create
    tenant_login = test_platform.Platform.tenant_login

    def prepare(self):
        site = self.create()
        app = self.dispatcher.application(site)
        with app.app_context():
            cat = Categoria(nome="Lanches")
            db.session.add(cat)
            db.session.flush()
            db.session.add(Produto(nome="Lanche", preco=2000, categoria_id=cat.id))
            db.session.add(
                Usuario(
                    nome="Garçom",
                    login="garcom",
                    senha=generate_password_hash("test-password"),
                    perfil="garcom",
                )
            )
            db.session.add(
                Usuario(
                    nome="Cozinha",
                    login="cozinha",
                    senha=generate_password_hash("test-password"),
                    perfil="cozinha",
                )
            )
            db.session.commit()
        return site, app

    def csrf_for(self, client, path="/r/loja-um/login"):
        return csrf(client.get(path))

    def api(self, client, path, data):
        token = self.csrf_for(client)
        return client.post(
            "/r/loja-um" + path, json=data, headers={"X-CSRF-Token": token}
        )

    def guest(self, name="Pessoa"):
        c = self.app.test_client()
        token = self.csrf_for(c, "/r/loja-um/salao")
        r = c.post("/r/loja-um/salao", data={"csrf": token, "nome": name, "numero_mesa":"4"})
        self.assertEqual(r.status_code, 302)
        return c

    def order(self, c, key="guest-key-12345678", q=1):
        r = self.api(
            c,
            "/api/salao/pedidos",
            {"chave": key, "itens": [{"id": 1, "quantidade": q}]},
        )
        self.assertIn(r.status_code, [200, 201], r.get_data(as_text=True))
        return r.json["id"]

    def waiter(self):
        c = self.app.test_client()
        token = self.csrf_for(c)
        r = c.post(
            "/r/loja-um/login",
            data={"csrf": token, "login": "garcom", "senha": "test-password"},
        )
        self.assertEqual(r.status_code, 302)
        return c

    def test_valid_registration_profile_and_email_login(self):
        site = self.create()
        with self.dispatcher.application(site).app_context():
            u = db.session.get(Usuario, 1)
            self.assertEqual(u.nome, "Administrador Teste")
        contact = self.registry.contact(site["id"], 1)
        self.assertNotIn("52998224725", contact["cpf_cifrado"])
        self.assertEqual(contact["bairro"], "Centro")
        token = self.csrf_for(self.client)
        r = self.client.post(
            "/r/loja-um/login",
            data={"csrf": token, "login": "admin", "senha": "test-password"},
        )
        self.assertNotEqual(r.status_code, 302)
        self.tenant_login("loja-um")

    def test_invalid_cpf_feedback_no_partial_restaurant(self):
        data = {
            "csrf": self.token,
            "nome": "Nome",
            "slug": "outra-loja",
            "admin_nome": "Pessoa",
            "email": "pessoa@example.com",
            "senha": "test-password",
            "meses": "1",
            "cpf": "11111111111",
            "nascimento": "1990-01-01",
            "endereco": "Rua",
            "numero": "1",
            "bairro": "Centro",
        }
        r = self.client.post(
            "/geral/restaurantes", data=data, headers={"Accept": "application/json"}
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("CPF", r.json["error"])
        self.assertIsNone(self.registry.site(slug="outra-loja"))
        data["cpf"] = "52998224725"
        data["slug"] = "Rua das Flores, 10"
        r = self.client.post(
            "/geral/restaurantes", data=data, headers={"Accept": "application/json"}
        )
        self.assertEqual(r.status_code, 400)

    def test_duplicate_email_forbidden_and_profile_update(self):
        site = self.create()
        path = f"/geral/restaurantes/{site['id']}/administradores"
        data = {
            "csrf": self.token,
            "acao": "criar",
            "nome": "Segundo",
            "email": "admin@example.com",
            "senha": "test-password",
            "cpf": "52998224725",
            "nascimento": "1990-01-01",
            "endereco": "Rua",
            "numero": "1",
            "bairro": "Centro",
        }
        self.assertEqual(self.client.post(path, data=data).status_code, 409)
        data.update(email="segundo@example.com")
        self.assertEqual(self.client.post(path, data=data).status_code, 302)
        data.update(acao="perfil", id=2, nome="Segundo Ajustado", bairro="Novo Bairro")
        self.assertEqual(self.client.post(path, data=data).status_code, 302)
        self.assertEqual(self.registry.contact(site["id"], 2)["bairro"], "Novo Bairro")
        self.assertIn("Segundo Ajustado", self.client.get(path).get_data(as_text=True))

    def test_owner_only_email_can_authenticate(self):
        c = self.app.test_client()
        token = csrf(c.get("/geral/login"))
        self.assertEqual(
            c.post(
                "/geral/login",
                data={"csrf": token, "login": "owner", "senha": "owner-password"},
            ).status_code,
            200,
        )
        self.assertEqual(
            c.post(
                "/geral/login",
                data={
                    "csrf": token,
                    "email": "OWNER@EXAMPLE.COM",
                    "senha": "owner-password",
                },
            ).status_code,
            302,
        )

    def test_password_protected_pages_and_exports(self):
        self.create()
        self.tenant_login("loja-um")
        pages = [
            "/clientes",
            "/loja",
            "/cadastros/produtos",
            "/cadastros/categorias",
            "/cadastros/usuarios",
            "/relatorios-vendas",
        ]
        for page in pages:
            r = self.client.get("/r/loja-um" + page)
            self.assertEqual(r.status_code, 302)
            self.assertIn("acesso-restrito", r.location)
        self.assertEqual(
            self.client.get("/r/loja-um/clientes/exportar.xlsx").status_code, 403
        )
        self.assertEqual(
            self.client.get("/r/loja-um/relatorios-vendas/exportar.xlsx").status_code,
            403,
        )
        path = "/r/loja-um/acesso-restrito?destino=/r/loja-um/clientes"
        token = self.csrf_for(self.client)
        r = self.client.post(path, data={"csrf": token, "senha": "errada"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Senha incorreta", r.get_data(as_text=True))
        self.assertEqual(self.client.get("/r/loja-um/clientes").status_code, 302)
        r = self.client.post(path, data={"csrf": token, "senha": "test-password"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/r/loja-um/clientes").status_code, 200)
        self.assertEqual(self.client.get("/r/loja-um/loja").status_code, 302)
        self.client.get(path)  # menu pede novamente
        self.assertEqual(self.client.get("/r/loja-um/clientes").status_code, 302)
        self.assertEqual(
            self.client.get(
                "/r/loja-um/acesso-restrito?destino=https://malicioso.test/clientes"
            ).status_code,
            400,
        )

    def test_same_comanda_append_and_different_table_blocked(self):
        site, app = self.prepare()
        c = self.waiter()
        data = {
            "comanda": "008",
            "numero_mesa": "2",
            "chave": "salon-key-12345678",
            "itens": [{"id": 1, "quantidade": 1}],
        }
        r = self.api(c, "/api/pedidos", data)
        self.assertEqual(r.status_code, 201)
        first = r.json["id"]
        self.assertEqual(self.api(c, "/api/pedidos", data).json["id"], first)
        data["chave"] = "salon-key-22222222"
        r = self.api(c, "/api/pedidos", data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["id"], first)
        data.update(numero_mesa="3", chave="salon-key-33333333")
        self.assertEqual(self.api(c, "/api/pedidos", data).status_code, 409)
        data.update(comanda="9", numero_mesa="2")
        self.assertEqual(self.api(c, "/api/pedidos", data).status_code, 201)
        with app.app_context():
            self.assertEqual(db.session.get(Pedido, first).total, 4000)
            self.assertEqual(
                db.session.scalar(db.select(db.func.count()).select_from(Pedido)), 2
            )

    def test_append_preserves_old_item_stage_and_blocks_paid(self):
        site, app = self.prepare()
        c = self.waiter()
        p = self.api(
            c,
            "/api/pedidos",
            {"comanda": "1", "numero_mesa": "1", "itens": [{"id": 1, "quantidade": 1}]},
        ).json["id"]
        with app.app_context():
            order = db.session.get(Pedido, p)
            order.status = "entregue"
            order.itens[0].etapa = "entregue"
            db.session.commit()
        r = self.api(
            c, f"/api/pedidos/{p}/itens", {"itens": [{"id": 1, "quantidade": 2}]}
        )
        self.assertEqual(r.status_code, 200)
        with app.app_context():
            order = db.session.get(Pedido, p)
            self.assertEqual(order.status, "aberto")
            self.assertEqual([i.etapa for i in order.itens], ["entregue", "aberto"])
            order.pago = True
            db.session.commit()
        self.assertEqual(
            self.api(
                c, f"/api/pedidos/{p}/itens", {"itens": [{"id": 1, "quantidade": 1}]}
            ).status_code,
            409,
        )

    def test_qr_privacy_idempotency_and_notifications(self):
        site, app = self.prepare()
        a = self.guest("A")
        b = self.guest("B")
        aid = self.order(a)
        bid = self.order(b)
        self.assertEqual(self.order(a), aid)
        self.assertEqual(
            [x["id"] for x in a.get("/r/loja-um/api/salao/pedidos").json], [aid]
        )
        self.assertEqual(
            a.get(f"/r/loja-um/api/pedidos/{bid}/detalhes").status_code, 403
        )
        for path in [
            "/api/pedidos",
            "/clientes",
            "/pdv",
            "/loja",
            "/relatorios-vendas",
        ]:
            self.assertEqual(a.get("/r/loja-um" + path).status_code, 403)
        w = self.waiter()
        self.assertIn(aid, [x["id"] for x in w.get("/r/loja-um/api/pedidos").json])
        self.assertEqual(
            self.api(
                a, f"/api/pedidos/{aid}/comanda", {"comanda": "1", "numero_mesa": "1"}
            ).status_code,
            403,
        )
        r = self.api(
            w, f"/api/pedidos/{aid}/comanda", {"comanda": "1", "numero_mesa": "1"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(a.get("/r/loja-um/api/salao/pedidos").json[0]["comanda"], "1")
        with app.app_context():
            p = db.session.get(Pedido, aid)
            p.status = "em_preparo"
            from notifications import emit_order

            emit_order(p, "em_preparo")
            db.session.commit()
        notices = a.get("/r/loja-um/api/notificacoes").json["items"]
        self.assertTrue(
            any(
                n["url"] == f"/r/loja-um/salao/meus-pedidos?pedido={aid}"
                for n in notices
            )
        )

    def test_two_guests_merge_comanda_keep_private_items(self):
        site, app = self.prepare()
        a = self.guest("A")
        b = self.guest("B")
        w = self.waiter()
        aid = self.order(a, q=1)
        bid = self.order(b, q=2)
        for id in [aid, bid]:
            r = self.api(
                w, f"/api/pedidos/{id}/comanda", {"comanda": "10", "numero_mesa": "4"}
            )
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        aa = a.get("/r/loja-um/api/salao/pedidos").json[0]
        bb = b.get("/r/loja-um/api/salao/pedidos").json[0]
        self.assertEqual(aa["id"], bb["id"])
        self.assertEqual(aa["total"], 2000)
        self.assertEqual(bb["total"], 4000)
        self.assertEqual(len(aa["itens"]), 1)
        self.assertEqual(len(bb["itens"]), 1)
        with app.app_context():
            self.assertEqual(
                db.session.scalar(db.select(db.func.count()).select_from(Pedido)), 1
            )
            self.assertEqual(db.session.get(Pedido, aid).total, 6000)
        self.assertEqual(self.order(b, q=2), aid)  # chave antiga acompanha merge

    def test_qr_delivery_requires_comanda_and_owner_cannot_be_forged(self):
        site, app = self.prepare()
        a = self.guest()
        aid = self.order(a)
        w = self.waiter()
        with app.app_context():
            p = db.session.get(Pedido, aid)
            p.status = "pronto"
            p.itens[0].etapa = "pronto"
            db.session.commit()
        self.assertEqual(
            self.api(
                w, f"/api/pedidos/{aid}/status", {"status": "entregue"}
            ).status_code,
            409,
        )
        r = self.api(
            w,
            f"/api/pedidos/{aid}/comanda",
            {"comanda": "3", "numero_mesa": "2", "entregar": True},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            a.get("/r/loja-um/api/salao/pedidos").json[0]["status"], "entregue"
        )
        self.assertEqual(a.get("/geral").status_code, 302)

    def test_qr_svg_scoped_to_restaurant(self):
        self.create()
        self.tenant_login("loja-um")
        r = self.client.get("/r/loja-um/qr-code.svg")
        self.assertEqual(r.status_code, 200)
        self.assertIn("svg", r.mimetype)
        self.assertIn(
            "/r/loja-um/salao",
            self.client.get("/r/loja-um/qr-code").get_data(as_text=True),
        )
        self.assertEqual(
            self.app.test_client().get("/r/loja-um/qr-code.svg").status_code, 403
        )

    def test_migration_preserves_existing_rows_and_backups(self):
        database = Path(self.temp.name) / "old.db"
        with sqlite3.connect(database) as c:
            c.executescript(
                "CREATE TABLE usuario(id INTEGER PRIMARY KEY); CREATE TABLE pedido(id INTEGER PRIMARY KEY,mesa TEXT,status TEXT); CREATE TABLE item(id INTEGER PRIMARY KEY,pedido_id INTEGER,nome TEXT,preco INTEGER,quantidade INTEGER); INSERT INTO pedido VALUES(1,'08','pronto');INSERT INTO item VALUES(1,1,'Lanche antigo',2500,2);"
            )
        app = create_app(
            {"SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(database), "TESTING": True}
        )
        with app.app_context():
            backup = migrate_current()
            self.assertTrue(backup.is_file())
            self.assertIsNone(migrate_current())
            with db.engine.connect() as conn:
                row = conn.exec_driver_sql("SELECT mesa,numero_mesa FROM pedido").one()
                self.assertEqual(tuple(row), ("08", ""))
                self.assertEqual(
                    conn.exec_driver_sql("SELECT etapa FROM item").scalar(), "pronto"
                )
                self.assertEqual(
                    conn.exec_driver_sql("SELECT preco*quantidade FROM item").scalar(),
                    5000,
                )
            with sqlite3.connect(backup) as c:
                self.assertNotIn(
                    "numero_mesa",
                    [x[1] for x in c.execute("PRAGMA table_info(pedido)")],
                )
            db.engine.dispose()

    def test_concurrent_staff_sends_use_one_comanda(self):
        site, app = self.prepare()
        first = self.waiter()
        second = self.waiter()
        tokens = [self.csrf_for(first), self.csrf_for(second)]
        barrier = threading.Barrier(2)

        def send(pair):
            index, client = pair
            barrier.wait(timeout=5)
            return client.post(
                "/r/loja-um/api/pedidos",
                json={
                    "comanda": "40",
                    "numero_mesa": "5",
                    "chave": "concurrent-send-key-" + str(index),
                    "itens": [{"id": 1, "quantidade": 1}],
                },
                headers={"X-CSRF-Token": tokens[index]},
            )

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(send, enumerate([first, second])))
        self.assertEqual(sorted(r.status_code for r in results), [200, 201])
        self.assertEqual(results[0].json["id"], results[1].json["id"])
        with app.app_context():
            self.assertEqual(
                db.session.scalar(db.select(db.func.count()).select_from(Pedido)), 1
            )
            self.assertEqual(db.session.scalar(db.select(Pedido)).total, 4000)

    def test_failed_registration_cleans_up_and_can_retry(self):
        from unittest.mock import patch

        data = {
            "csrf": self.token,
            "nome": "Teste",
            "slug": "teste-falha",
            "admin_nome": "Pessoa Teste",
            "email": "pessoa@example.com",
            "senha": "test-password",
            "meses": "1",
            "cpf": "52998224725",
            "nascimento": "1990-01-01",
            "endereco": "Rua",
            "numero": "1",
            "bairro": "Centro",
        }
        with patch("setup_push.setup", side_effect=OSError("simulated disk failure")):
            r = self.client.post(
                "/geral/restaurantes", data=data, headers={"Accept": "application/json"}
            )
        self.assertEqual(r.status_code, 503)
        self.assertIsNone(self.registry.site(slug="teste-falha"))
        self.assertFalse(list((self.registry.root / "restaurantes").glob("*")))
        self.assertEqual(
            self.client.post("/geral/restaurantes", data=data).status_code, 302
        )

    def test_qr_linking_to_wrong_table_rolls_back(self):
        site, app = self.prepare()
        w = self.waiter()
        self.api(
            w,
            "/api/pedidos",
            {"comanda": "5", "numero_mesa": "1", "itens": [{"id": 1, "quantidade": 1}]},
        )
        guest = self.guest()
        id = self.order(guest)
        r = self.api(
            w, f"/api/pedidos/{id}/comanda", {"comanda": "5", "numero_mesa": "2"}
        )
        self.assertEqual(r.status_code, 409)
        row = guest.get("/r/loja-um/api/salao/pedidos").json[0]
        self.assertTrue(row["aguardando_comanda"])
        self.assertEqual(row["total"], 2000)
        self.assertEqual(
            guest.post(
                "/r/loja-um/api/salao/pedidos",
                json={
                    "chave": "missing-csrf-key",
                    "itens": [{"id": 1, "quantidade": 1}],
                },
            ).status_code,
            400,
        )

    def test_valid_management_password_does_not_exhaust_attempts(self):
        self.create()
        self.tenant_login("loja-um")
        token = self.csrf_for(self.client)
        for _ in range(10):
            response = self.client.post(
                "/r/loja-um/acesso-restrito?destino=/r/loja-um/clientes",
                data={"csrf": token, "senha": "test-password"},
            )
            self.assertEqual(response.status_code, 302)

    def test_area_grant_expires(self):
        from unittest.mock import patch

        self.create()
        self.tenant_login("loja-um")
        token = self.csrf_for(self.client)
        self.client.post(
            "/r/loja-um/acesso-restrito?destino=/r/loja-um/clientes",
            data={"csrf": token, "senha": "test-password"},
        )
        self.assertEqual(self.client.get("/r/loja-um/clientes").status_code, 200)
        with patch("management_access.time.time", return_value=time.time() + 301):
            self.assertEqual(self.client.get("/r/loja-um/clientes").status_code, 302)
            self.assertEqual(
                self.client.get("/r/loja-um/clientes/exportar.xlsx").status_code, 403
            )


if __name__ == "__main__":
    unittest.main()
