import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import date
from werkzeug.security import generate_password_hash
from cryptography.fernet import Fernet
from app import create_app
from models import (
    db,
    Usuario,
    Cliente,
    Categoria,
    Produto,
    Loja,
    Pedido,
    Notificacao,
    EnvioPedido,
)
from customer_security import cpf_valido


def synthetic_cpf(base="987654320"):
    for size in [9, 10]:
        n = sum(int(base[i]) * (size + 1 - i) for i in range(size)) * 10 % 11
        base += str(0 if n == 10 else n)
    return base


class Online(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch("customer_security.DATA", Path(self.temp.name))
        self.patch.start()
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
        for role in ["admin", "garcom", "cozinha"]:
            db.session.add(
                Usuario(
                    nome=role,
                    login=role,
                    senha=generate_password_hash("test-password"),
                    perfil=role,
                )
            )
        category = Categoria(nome="Pratos")
        db.session.add(category)
        db.session.flush()
        db.session.add(Produto(nome="Prato", preco=2500, categoria_id=category.id))
        db.session.add(
            Loja(
                id=1,
                nome="Loja Teste",
                taxa_entrega=600,
                entrega_ativa=True,
                pedidos_ativos=True,
            )
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.patch.stop()
        self.temp.cleanup()

    def csrf(self):
        self.client.get("/login")
        with self.client.session_transaction() as s:
            return s["csrf"]

    def post_form(self, url, data):
        return self.client.post(url, data={**data, "csrf": self.csrf()})

    def post(self, url, data):
        return self.client.post(url, json=data, headers={"X-CSRF-Token": self.csrf()})

    def logout(self):
        self.post_form("/logout", {})

    def login(self, name):
        r = self.post_form("/login", {"login": name, "senha": "test-password"})
        self.assertEqual(r.status_code, 302)

    def register(self, name="cliente1", base="987654320", **extra):
        self.logout()
        data = dict(
            nome="Cliente " + name,
            login=name,
            senha="test-password",
            confirmar_senha="test-password",
            cpf=synthetic_cpf(base),
            nascimento="1990-05-12",
            modalidade="retirada",
        )
        data.update(extra)
        return self.post_form("/cadastro", data)

    def payload(self, **extra):
        data = dict(
            chave="1234567890abcdef1234567890abcdef",
            modalidade="retirada",
            forma_pagamento="pix",
            itens=[{"id": 1, "quantidade": 2, "observacao": "Sem sal"}],
            total_previsto=5000,
        )
        data.update(extra)
        return data

    def test_public_menu_and_safe_registration(self):
        self.assertEqual(self.client.get("/cardapio").status_code, 200)
        self.assertEqual(self.client.get("/api/cliente/pedidos").status_code, 401)
        r = self.register(perfil="admin")
        self.assertEqual(r.status_code, 302)
        user = db.session.scalar(db.select(Usuario).where(Usuario.login == "cliente1"))
        self.assertEqual(user.perfil, "cliente")
        c = db.session.scalar(db.select(Cliente))
        self.assertEqual(c.endereco, "")
        self.assertNotIn(synthetic_cpf(), c.cpf_cifrado)
        key = (Path(self.temp.name) / "customer-data.key").read_bytes()
        self.assertEqual(
            Fernet(key).decrypt(c.cpf_cifrado.encode()).decode(), synthetic_cpf()
        )
        for page in ["/cardapio", "/meus-pedidos", "/minha-conta"]:
            self.assertEqual(self.client.get(page).status_code, 200, page)

    def test_invalid_cpf_dob_and_duplicate(self):
        for value in [
            "11111111111",
            "123",
            "ABC12345678",
            synthetic_cpf()[:-1] + str((int(synthetic_cpf()[-1]) + 1) % 10),
        ]:
            self.assertFalse(cpf_valido(value))
        self.assertEqual(self.register(cpf="11111111111").status_code, 200)
        self.assertIsNone(db.session.scalar(db.select(Cliente)))
        self.assertEqual(self.register(nascimento="2999-01-01").status_code, 200)
        self.assertIsNone(db.session.scalar(db.select(Cliente)))
        self.assertEqual(self.register().status_code, 302)
        self.assertEqual(self.register(name="cliente2").status_code, 200)
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(Cliente)), 1
        )

    def test_delivery_registration_requires_address(self):
        self.assertEqual(self.register(modalidade="entrega").status_code, 200)
        self.assertIsNone(db.session.scalar(db.select(Cliente)))
        self.assertEqual(
            self.register(
                modalidade="entrega",
                endereco="Rua Teste",
                bairro="Centro",
                numero="10",
                referencia="Ao lado da praça",
            ).status_code,
            302,
        )
        self.assertEqual(db.session.scalar(db.select(Cliente)).bairro, "Centro")

    def test_customer_is_blocked_from_all_internal_operations(self):
        self.register()
        for url in [
            "/pdv",
            "/pedidos",
            "/api/pedidos",
            "/dashboard",
            "/caixa",
            "/cadastros/usuarios",
            "/cadastros/produtos",
            "/cadastros/categorias",
            "/clientes",
            "/loja",
        ]:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.assertEqual(
            self.post(
                "/api/pedidos", {"mesa": "1", "itens": [{"id": 1, "quantidade": 1}]}
            ).status_code,
            403,
        )

    def test_pickup_idempotent_and_isolated(self):
        self.register()
        payload = self.payload()
        r = self.post("/api/cliente/pedidos", payload)
        self.assertEqual(r.status_code, 201)
        id = r.json["id"]
        again = self.post("/api/cliente/pedidos", payload)
        self.assertEqual(again.json["id"], id)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(
            self.post(
                "/api/cliente/pedidos", self.payload(itens=[{"id": 1, "quantidade": 1}])
            ).status_code,
            409,
        )
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(Pedido)), 1
        )
        p = db.session.get(Pedido, id)
        self.assertFalse(p.pago)
        self.assertEqual(p.total, 5000)
        self.assertEqual(p.online.endereco, "")
        self.assertEqual(
            self.client.get("/api/cliente/envios/" + payload["chave"]).json["id"], id
        )
        self.register(name="cliente2", base="876543210")
        self.assertEqual(self.client.get("/api/cliente/pedidos").json, [])
        self.assertIsNone(
            self.client.get("/api/cliente/envios/" + payload["chave"]).json["id"]
        )

    def test_delivery_address_fee_and_change(self):
        self.register()
        self.assertEqual(
            self.post(
                "/api/cliente/pedidos", self.payload(modalidade="entrega")
            ).status_code,
            400,
        )
        payload = self.payload(
            modalidade="entrega",
            endereco="Rua Teste",
            numero="s/n",
            bairro="Centro",
            referencia="Portão azul",
            forma_pagamento="dinheiro",
            troco_para="100",
            total_previsto=5600,
        )
        r = self.post("/api/cliente/pedidos", payload)
        self.assertEqual(r.status_code, 201)
        p = db.session.get(Pedido, r.json["id"])
        self.assertEqual(p.total, 5600)
        self.assertEqual(p.online.troco_para, 10000)
        loja = db.session.get(Loja, 1)
        loja.taxa_entrega = 900
        db.session.commit()
        self.assertEqual(p.total, 5600)
        c = db.session.scalar(db.select(Cliente))
        c.endereco = "Outra rua"
        db.session.commit()
        self.assertEqual(p.online.endereco, "Rua Teste")

    def test_total_and_change_validation(self):
        self.register()
        self.assertEqual(
            self.post(
                "/api/cliente/pedidos",
                self.payload(forma_pagamento="dinheiro", troco_para="10"),
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post(
                "/api/cliente/pedidos", self.payload(total_previsto=1)
            ).status_code,
            409,
        )
        self.assertEqual(
            self.post(
                "/api/cliente/pedidos", self.payload(forma_pagamento="falso")
            ).status_code,
            400,
        )
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(Pedido)), 0
        )

    def test_staff_visibility_and_online_data_minimization(self):
        self.register()
        online = self.post(
            "/api/cliente/pedidos",
            self.payload(
                modalidade="entrega",
                endereco="Rua Privada",
                numero="1",
                bairro="Centro",
                referencia="Teste",
                total_previsto=5600,
            ),
        ).json["id"]
        self.login("garcom")
        salon = self.post(
            "/api/pedidos", {"mesa": "08", "itens": [{"id": 1, "quantidade": 1}]}
        ).json["id"]
        self.assertEqual(
            [p["id"] for p in self.client.get("/api/pedidos").json], [salon]
        )
        self.assertEqual(
            self.post(
                f"/api/pedidos/{online}/status", {"status": "em_preparo"}
            ).status_code,
            403,
        )
        data = self.client.get("/api/notificacoes").get_data(as_text=True)
        self.assertNotIn("Tele-entrega", data)
        self.login("cozinha")
        orders = self.client.get("/api/pedidos").json
        self.assertEqual(len(orders), 2)
        external = next(p for p in orders if p["id"] == online)
        self.assertNotIn("endereco", external)
        self.assertNotIn("cpf", json.dumps(external))
        self.assertNotIn("nascimento", json.dumps(external))
        self.login("admin")
        external = next(
            p for p in self.client.get("/api/pedidos").json if p["id"] == online
        )
        self.assertEqual(external["endereco"]["endereco"], "Rua Privada")

    def test_roles_and_navigation(self):
        for role in ["garcom", "cozinha"]:
            self.login(role)
            for url in [
                "/clientes",
                "/loja",
                "/dashboard",
                "/caixa",
                "/cadastros/usuarios",
                "/minha-conta",
                "/meus-pedidos",
            ]:
                self.assertEqual(self.client.get(url).status_code, 403, (role, url))
            self.assertEqual(self.client.get("/pedidos").status_code, 200)
            self.assertEqual(self.client.get("/cardapio").status_code, 302)
        self.assertEqual(self.client.get("/pdv").status_code, 403)
        self.login("admin")
        for url in [
            "/clientes",
            "/loja",
            "/dashboard",
            "/caixa",
            "/cadastros/usuarios",
            "/cardapio",
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_online_full_delivery_flow_and_receipt_permissions(self):
        self.register()
        id = self.post(
            "/api/cliente/pedidos",
            self.payload(
                modalidade="entrega",
                endereco="Rua Teste",
                numero="1",
                bairro="Centro",
                referencia="Teste",
                total_previsto=5600,
            ),
        ).json["id"]
        self.assertEqual(
            self.post(
                f"/api/pedidos/{id}/status", {"status": "em_preparo"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.post(f"/api/pedidos/{id}/pagar", {"forma": "pix"}).status_code, 403
        )
        self.login("cozinha")
        for state in ["em_preparo", "pronto"]:
            self.assertEqual(
                self.post(f"/api/pedidos/{id}/status", {"status": state}).status_code,
                200,
            )
        self.assertEqual(
            self.post(
                f"/api/pedidos/{id}/status", {"status": "saiu_entrega"}
            ).status_code,
            403,
        )
        self.login("admin")
        for state in ["saiu_entrega", "entregue"]:
            self.assertEqual(
                self.post(f"/api/pedidos/{id}/status", {"status": state}).status_code,
                200,
            )
        self.login("cliente1")
        items = self.client.get("/api/cliente/pedidos").json
        self.assertEqual(items[0]["status"], "entregue")
        notices = self.client.get("/api/notificacoes").json["items"]
        self.assertTrue(
            any(
                n["tipo"] == "saiu_entrega" and n["url"] == f"/meus-pedidos?pedido={id}"
                for n in notices
            )
        )

    def test_store_pauses_and_management_separation(self):
        self.register()
        c = db.session.scalar(db.select(Cliente))
        client_uid = c.usuario_id
        self.login("admin")
        self.assertEqual(
            self.client.get(
                "/cadastros/usuarios?editar=" + str(client_uid)
            ).status_code,
            403,
        )
        self.assertEqual(
            self.post_form(
                "/loja",
                {"nome": "Nova loja", "taxa_entrega": "8.50", "entrega_ativa": "on"},
            ).status_code,
            302,
        )
        self.login("cliente1")
        self.assertEqual(
            self.post("/api/cliente/pedidos", self.payload()).status_code, 409
        )
        loja = db.session.get(Loja, 1)
        loja.pedidos_ativos = True
        loja.entrega_ativa = False
        db.session.commit()
        self.assertEqual(
            self.post(
                "/api/cliente/pedidos", self.payload(modalidade="entrega")
            ).status_code,
            409,
        )

    def test_malformed_payload_and_csrf(self):
        self.register()
        self.assertEqual(
            self.client.post("/api/cliente/pedidos", json=self.payload()).status_code,
            400,
        )
        self.assertEqual(self.post("/api/cliente/pedidos", []).status_code, 400)
        self.assertEqual(
            self.post("/api/cliente/pedidos", self.payload(chave="x")).status_code, 400
        )
        self.assertEqual(
            self.post(
                "/api/cliente/pedidos",
                self.payload(itens=[{"id": 1, "quantidade": -1}]),
            ).status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
