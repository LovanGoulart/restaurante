"""Exclusão lógica, política de menus, notificações e migração aditiva."""

import unittest
from pathlib import Path
import tempfile, sqlite3
from app import create_app
from models import (
    db,
    Produto,
    Categoria,
    Pedido,
    Item,
    Loja,
    Usuario,
    Notificacao,
    Cliente,
    PedidoOnline,
)
from product_options import size_cards
from notifications import emit_order
from atualizar_sistema import migrate_current
import test_product_options as fixture
import test_pizza_flavors as pizza_fixture


class OperationUpgrade(unittest.TestCase):
    setUp = fixture.Options.setUp
    tearDown = fixture.Options.tearDown
    login = fixture.Options.login
    post = fixture.Options.post

    def test_product_exclusion_keeps_order_snapshot_and_rejects_new_sales(self):
        order = Pedido(mesa="5", numero_mesa="1", usuario_id=1)
        order.itens = [Item(nome="Pizza de teste", preco=5000, quantidade=1)]
        db.session.add(order)
        db.session.commit()
        id = order.id
        self.assertEqual(
            self.post("/cadastros/produtos/1/excluir", {}).status_code, 302
        )
        self.assertTrue(db.session.get(Produto, 1).excluido)
        self.assertFalse(db.session.get(Produto, 1).ativo)
        self.assertEqual(db.session.get(Pedido, id).total, 5000)
        self.assertNotIn(
            'data-product="1"', self.client.get("/pdv").get_data(as_text=True)
        )
        self.assertNotIn(
            "Opções do produto →",
            self.client.get("/cadastros/produtos").get_data(as_text=True),
        )
        self.assertEqual(
            self.client.get("/cadastros/produtos/1/opcoes").status_code, 404
        )
        self.assertEqual(
            self.post(
                "/api/pedidos",
                {
                    "comanda": "9",
                    "numero_mesa": "1",
                    "itens": [{"id": 1, "quantidade": 1}],
                },
            ).status_code,
            400,
        )

    def test_category_requires_moving_products_and_can_be_recreated(self):
        with self.client.session_transaction() as session:
            session["management_grants"] = {"produtos": True, "categorias": True}
        self.assertEqual(
            self.post("/cadastros/categorias/1/excluir", {}).status_code, 409
        )
        self.assertEqual(
            self.post("/cadastros/produtos/1/excluir", {}).status_code, 302
        )
        self.assertEqual(
            self.post("/cadastros/categorias/1/excluir", {}).status_code, 302
        )
        self.assertTrue(db.session.get(Categoria, 1).excluido)
        r = self.client.post(
            "/cadastros/categorias", data={"csrf": "token", "nome": "Pizzas"}
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(db.session.get(Categoria, 1).excluido)

    def test_delete_permissions_and_csrf(self):
        self.assertEqual(
            self.client.post("/cadastros/produtos/1/excluir").status_code, 400
        )
        for id in [2, 3]:
            self.login(id)
            self.assertEqual(
                self.post("/cadastros/produtos/1/excluir", {}).status_code, 403
            )
        self.login(1)
        self.assertEqual(
            self.post("/cadastros/usuarios/1/excluir", {}).status_code, 403
        )

    def test_grants_do_not_expire_and_menu_does_not_reset_them(self):
        with self.client.session_transaction() as s:
            s["management_grants"] = {"produtos": 1}
        self.assertEqual(self.client.get("/cadastros/produtos").status_code, 200)
        self.assertEqual(
            self.client.get("/acesso-restrito?destino=/cadastros/produtos").status_code,
            302,
        )
        self.assertEqual(self.client.get("/cadastros/produtos").status_code, 200)
        self.post("/bloquear-gestao", {})
        self.assertEqual(self.client.get("/cadastros/produtos").status_code, 302)

    def test_policy_persists_requires_password_and_does_not_open_staff_access(self):
        r = self.client.post(
            "/seguranca-gestao", data={"csrf": "token", "senha": "wrong"}
        )
        self.assertIn("Senha incorreta", r.get_data(as_text=True))
        r = self.client.post(
            "/seguranca-gestao", data={"csrf": "token", "senha": "test-password"}
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(db.session.get(Loja, 1).bloquear_menus)
        with self.client.session_transaction() as s:
            s["management_grants"] = {}
        self.assertEqual(self.client.get("/cadastros/produtos").status_code, 200)
        self.assertEqual(self.client.get("/cadastros/categorias").status_code, 200)
        self.login(2)
        self.assertEqual(self.client.get("/seguranca-gestao").status_code, 403)
        self.assertEqual(self.client.get("/cadastros/produtos").status_code, 403)
        self.login(1)
        self.client.post(
            "/seguranca-gestao",
            data={"csrf": "token", "senha": "test-password", "bloquear_menus": "on"},
        )
        self.assertEqual(self.client.get("/cadastros/produtos").status_code, 302)

    def test_size_cards_and_starting_price_include_required_extras(self):
        config = pizza_fixture.PizzaFlavors.config(self)
        # Os helpers da fixture consultam somente o produto no banco atual.
        self.assertEqual(
            self.post("/cadastros/produtos/1/opcoes", config).status_code, 200
        )
        cards = size_cards(db.session.get(Produto, 1))
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["label"], "Broto · 4 fatias")
        self.assertEqual(cards[0]["from_price"], 5000)
        self.assertEqual(cards[1]["limit"], 6)
        html = self.client.get("/pdv").get_data(as_text=True)
        self.assertIn('data-size="large"', html)
        self.assertIn("A partir de R$ 65,00", html)

    def test_customer_ready_notifications_follow_order_channel(self):
        client = Usuario(
            nome="Cliente", login="cliente", senha="unused", perfil="cliente"
        )
        db.session.add(client)
        db.session.flush()
        customer = Cliente(
            usuario_id=client.id,
            cpf_cifrado="fake",
            cpf_hash="f" * 64,
            cpf_final="00",
            nascimento=__import__("datetime").date(1990, 1, 1),
        )
        db.session.add(customer)
        db.session.flush()
        for mode in ["entrega", "retirada", "salao"]:
            order = Pedido(
                mesa="8", numero_mesa="2", usuario_id=client.id, status="pronto"
            )
            db.session.add(order)
            db.session.flush()
            if mode != "salao":
                db.session.add(
                    PedidoOnline(
                        pedido_id=order.id,
                        cliente_id=customer.id,
                        modalidade=mode,
                        destinatario="Cliente",
                        forma_pagamento="pix",
                        taxa_entrega=0,
                    )
                )
                db.session.flush()
                db.session.expire(order, ["online"])
            emit_order(order, "pronto")
            db.session.commit()
            notification = db.session.scalar(
                db.select(Notificacao).where(
                    Notificacao.pedido_id == order.id,
                    Notificacao.usuario_id == client.id,
                )
            )
            if mode == "entrega":
                self.assertEqual(
                    notification.mensagem, "Seu pedido está indo até você."
                )
            elif mode == "retirada":
                self.assertIn(
                    "Vem rapidinho para não esfriar viu!", notification.mensagem
                )
            else:
                self.assertEqual(notification.mensagem, "Seu pedido está pronto.")

    def test_migration_adds_columns_without_changing_old_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "old.db"
            with sqlite3.connect(file) as connection:
                connection.executescript(
                    "CREATE TABLE categoria(id INTEGER PRIMARY KEY,nome TEXT); INSERT INTO categoria VALUES(1,'Antiga'); CREATE TABLE produto(id INTEGER PRIMARY KEY,nome TEXT); INSERT INTO produto VALUES(1,'Prato'); CREATE TABLE loja(id INTEGER PRIMARY KEY,nome TEXT); INSERT INTO loja VALUES(1,'Loja'); CREATE TABLE pedido(id INTEGER PRIMARY KEY,numero_mesa TEXT,status TEXT); CREATE TABLE item(id INTEGER PRIMARY KEY,visitante_id INTEGER,etapa TEXT);"
                )
            app = create_app(
                {
                    "TESTING": True,
                    "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(file),
                    "DATA_DIR": directory,
                }
            )
            with app.app_context():
                backup = migrate_current()
                self.assertTrue(backup.is_file())
                self.assertIsNone(migrate_current())
                with sqlite3.connect(file) as connection:
                    self.assertEqual(
                        connection.execute(
                            "SELECT nome,excluido FROM produto"
                        ).fetchone(),
                        ("Prato", 0),
                    )
                    self.assertEqual(
                        connection.execute(
                            "SELECT bloquear_menus FROM loja"
                        ).fetchone()[0],
                        1,
                    )
                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
