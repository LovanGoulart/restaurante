import re
import tempfile
import unittest
import sqlite3
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash
from app import create_app
from platform_admin import create_platform, utcnow, add_months, valid_email
from models import db, Usuario, Categoria, Produto, Pedido, Item


def csrf(response):
    return re.search(
        r'name="csrf" value="([^"]+)"', response.get_data(as_text=True)
    ).group(1)


class Platform(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_platform(create_app, Path(self.temp.name) / "platform")
        self.app.config["TESTING"] = True
        self.dispatcher = self.app.extensions["restaurant_platform"]
        self.registry = self.dispatcher.registry
        with self.registry.connect() as c:
            c.execute(
                "INSERT INTO owner(id,name,login,email,password) VALUES(1,?,?,?,?)",
                (
                    "Owner",
                    "owner",
                    "owner@example.com",
                    generate_password_hash("owner-password"),
                ),
            )
        self.client = self.app.test_client()
        token = csrf(self.client.get("/geral/login"))
        r = self.client.post(
            "/geral/login",
            data={
                "csrf": token,
                "login": "owner@example.com",
                "senha": "owner-password",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.token = csrf(self.client.get("/geral"))

    def tearDown(self):
        for app in self.dispatcher.apps.values():
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        self.temp.cleanup()

    def create(self, slug="loja-um"):
        r = self.client.post(
            "/geral/restaurantes",
            data={
                "csrf": self.token,
                "nome": slug,
                "admin_nome": "Administrador Teste",
                "cpf": "529.982.247-25",
                "nascimento": "1990-05-12",
                "endereco": "Rua Teste",
                "numero": "10",
                "bairro": "Centro",
                "slug": slug,
                "login": "admin@example.com",
                "email": "admin@example.com",
                "senha": "test-password",
                "meses": "1",
            },
        )
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True))
        return self.registry.site(slug=slug)

    def tenant_login(self, slug):
        page = self.client.get(f"/r/{slug}/login")
        self.assertEqual(page.status_code, 200, page.get_data(as_text=True))
        token = csrf(page)
        r = self.client.post(
            f"/r/{slug}/login",
            data={
                "csrf": token,
                "login": "admin@example.com",
                "senha": "test-password",
            },
        )
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True))
        self.assertTrue(r.location.startswith(f"/r/{slug}/"))
        self.assertIn(f"Path=/r/{slug}/", r.headers["Set-Cookie"])
        return csrf(self.client.get(f"/r/{slug}/pedidos"))

    def test_isolation_and_prefixes(self):
        a = self.create()
        b = self.create("loja-dois")
        for site, label in [(a, "Privado A"), (b, "Privado B")]:
            with self.dispatcher.application(site).app_context():
                category = Categoria(nome="Mesma categoria")
                db.session.add(category)
                db.session.flush()
                db.session.add(
                    Produto(nome=label, categoria_id=category.id, preco=1000)
                )
                user = db.session.scalar(db.select(Usuario))
                p = Pedido(mesa=label, usuario_id=user.id)
                p.itens.append(Item(nome=label, preco=1000, quantidade=1))
                db.session.add(p)
                db.session.commit()
        self.tenant_login("loja-um")
        self.tenant_login("loja-dois")
        ra = self.client.get("/r/loja-um/api/pedidos")
        rb = self.client.get("/r/loja-dois/api/pedidos")
        self.assertEqual(ra.status_code, 200)
        self.assertEqual(rb.status_code, 200)
        self.assertEqual(ra.json[0]["mesa"], "Privado A")
        self.assertEqual(rb.json[0]["mesa"], "Privado B")
        for slug in ["loja-um", "loja-dois"]:
            page = self.client.get(f"/r/{slug}/pdv").get_data(as_text=True)
            self.assertIn(f'content="/r/{slug}"', page)
            self.assertNotIn('href="/pdv"', page)
            manifest = self.client.get(f"/r/{slug}/manifest.webmanifest").json
            self.assertEqual(manifest["scope"], f"/r/{slug}/")
            self.assertEqual(manifest["start_url"], f"/r/{slug}/")
        from appearance import settings, save

        # Arquivos de identidade não se misturam entre apps.
        app_a = self.dispatcher.application(a)
        app_b = self.dispatcher.application(b)
        with app_a.app_context():
            from config import data_dir

            (data_dir() / "appearance.json").write_text('{"navy":"#123456"}')
            self.assertEqual(settings()["navy"], "#123456")
        with app_b.app_context():
            self.assertNotEqual(settings()["navy"], "#123456")
        self.assertNotEqual(app_a.config["SECRET_KEY"], app_b.config["SECRET_KEY"])
        self.assertEqual(self.client.get("/api/pedidos").status_code, 404)
        self.assertEqual(self.client.get("/r/loja-um/geral").status_code, 404)

    def test_expiration_suspension_and_renewal(self):
        site = self.create()
        self.tenant_login(site["slug"])
        with self.registry.connect() as c:
            c.execute(
                "UPDATE restaurants SET expires=? WHERE id=?",
                ((utcnow() - timedelta(seconds=1)).isoformat(), site["id"]),
            )
        self.assertEqual(self.client.get("/r/loja-um/api/pedidos").status_code, 403)
        self.assertEqual(self.client.get("/r/loja-um/cardapio").status_code, 403)
        r = self.client.post(
            f"/geral/restaurantes/{site['id']}/plano",
            data={"csrf": self.token, "acao": "ativar"},
        )
        self.assertEqual(r.status_code, 409)
        for months in [1, 3, 6, 12]:
            r = self.client.post(
                f"/geral/restaurantes/{site['id']}/plano",
                data={"csrf": self.token, "acao": "renovar", "meses": months},
            )
            self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/r/loja-um/api/pedidos").status_code, 200)
        self.client.post(
            f"/geral/restaurantes/{site['id']}/plano",
            data={"csrf": self.token, "acao": "suspender"},
        )
        self.assertEqual(self.client.get("/r/loja-um/login").status_code, 403)
        self.client.post(
            f"/geral/restaurantes/{site['id']}/plano",
            data={"csrf": self.token, "acao": "ativar"},
        )
        self.assertEqual(self.client.get("/r/loja-um/login").status_code, 200)

    def test_admin_cannot_manage_other_admins_or_owner(self):
        site = self.create()
        token = self.tenant_login(site["slug"])
        self.client.post(
            "/r/loja-um/acesso-restrito?destino=/r/loja-um/cadastros/usuarios",
            data={"csrf": token, "senha": "test-password"},
        )
        data = {
            "csrf": token,
            "nome": "Attack",
            "login": "attack",
            "senha": "test-password",
            "perfil": "admin",
            "ativo": "on",
        }
        self.assertEqual(
            self.client.post("/r/loja-um/cadastros/usuarios", data=data).status_code,
            400,
        )
        data.update(id=1, perfil="garcom")
        self.assertEqual(
            self.client.post("/r/loja-um/cadastros/usuarios", data=data).status_code,
            403,
        )
        stranger = self.app.test_client()
        self.assertEqual(stranger.get("/geral").status_code, 302)
        self.assertEqual(
            stranger.post(
                f"/geral/restaurantes/{site['id']}/plano", data={"acao": "ativar"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/geral/restaurantes", data={"csrf": "wrong"}).status_code,
            400,
        )

    def test_email_and_owner_controls(self):
        for bad in [
            "",
            "sem-arroba",
            "a@local",
            "a..b@example.com",
            "a@example.com\nBAD",
            "a@-domain.com",
        ]:
            with self.assertRaises(ValueError):
                valid_email(bad)
        self.assertEqual(
            valid_email("nome+teste@EXAMPLE.COM"), "nome+teste@example.com"
        )
        site = self.create()
        path = f"/geral/restaurantes/{site['id']}/administradores"
        self.assertEqual(self.client.get(path).status_code, 200)
        r = self.client.post(
            path,
            data={
                "csrf": self.token,
                "acao": "criar",
                "nome": "Segundo",
                "cpf": "529.982.247-25",
                "nascimento": "1990-05-12",
                "endereco": "Rua Teste",
                "numero": "10",
                "bairro": "Centro",
                "login": "segundo@example.com",
                "email": "bad",
                "senha": "test-password",
            },
        )
        self.assertEqual(r.status_code, 400)
        r = self.client.post(
            path,
            data={
                "csrf": self.token,
                "acao": "criar",
                "nome": "Segundo",
                "cpf": "529.982.247-25",
                "nascimento": "1990-05-12",
                "endereco": "Rua Teste",
                "numero": "10",
                "bairro": "Centro",
                "login": "segundo@example.com",
                "email": "segundo@example.com",
                "senha": "test-password",
            },
        )
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True))
        self.assertEqual(
            self.registry.admin_email(site["id"], 2), "segundo@example.com"
        )
        self.client.post(path, data={"csrf": self.token, "acao": "desativar", "id": 1})
        page = self.client.get("/r/loja-um/login")
        token = csrf(page)
        r = self.client.post(
            "/r/loja-um/login",
            data={
                "csrf": token,
                "login": "admin@example.com",
                "senha": "test-password",
            },
        )
        self.assertNotEqual(r.status_code, 302)
        self.client.post(path, data={"csrf": self.token, "acao": "ativar", "id": 1})
        self.tenant_login(site["slug"])

    def test_calendar_months(self):
        jan = datetime(2024, 1, 31, 15, tzinfo=timezone.utc)
        self.assertEqual(add_months(jan, 1).day, 29)
        self.assertEqual(add_months(jan, 12).year, 2025)

    def test_missing_email_and_password_reset_revoke_session(self):
        site = self.create()
        self.tenant_login(site["slug"])
        path = f"/geral/restaurantes/{site['id']}/administradores"
        response = self.client.post(
            path,
            data={
                "csrf": self.token,
                "acao": "senha",
                "id": 1,
                "senha": "new-test-password",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/r/loja-um/api/pedidos").status_code, 403)
        page = self.client.get("/r/loja-um/login")
        token = csrf(page)
        self.assertEqual(
            self.client.post(
                "/r/loja-um/login",
                data={
                    "csrf": token,
                    "login": "admin@example.com",
                    "senha": "new-test-password",
                },
            ).status_code,
            302,
        )
        with self.registry.connect() as c:
            c.execute("DELETE FROM admin_contacts WHERE restaurant_id=?", (site["id"],))
        self.assertEqual(self.client.get("/r/loja-um/api/pedidos").status_code, 403)

    def test_media_files_and_notification_links_are_scoped(self):
        site = self.create()
        other = self.create("loja-dois")
        self.tenant_login(site["slug"])
        for current, content in [(site, b"A"), (other, b"B")]:
            folder = Path(current["folder"]) / "media"
            folder.mkdir()
            (folder / ("a" * 32 + ".jpg")).write_bytes(content)
        response = self.client.get("/r/loja-um/media/" + ("a" * 32) + ".jpg")
        self.assertEqual(response.data, b"A")
        response.close()
        response = self.client.get("/r/loja-dois/media/" + ("a" * 32) + ".jpg")
        self.assertEqual(response.data, b"B")
        response.close()
        self.assertEqual(
            self.client.get("/media/" + ("a" * 32) + ".jpg").status_code, 404
        )
        with self.dispatcher.application(site).app_context():
            from models import Notificacao

            db.session.add(
                Notificacao(
                    usuario_id=1,
                    pedido_id=1,
                    titulo="Teste",
                    mensagem="Teste",
                    tipo="novo",
                    alerta=True,
                )
            )
            db.session.commit()
        notice = self.client.get("/r/loja-um/api/notificacoes").json["items"][0]
        self.assertEqual(notice["url"], "/r/loja-um/pedidos?pedido=1")

    def test_legacy_adoption_preserves_database(self):
        import setup_geral

        folder = Path(self.temp.name) / "legacy"
        folder.mkdir()
        database = folder / "restaurante.db"
        with sqlite3.connect(database) as c:
            c.execute("CREATE TABLE usuario(id INTEGER PRIMARY KEY,perfil TEXT)")
            c.execute("INSERT INTO usuario VALUES(1,'admin')")
            c.execute("CREATE TABLE pedido(id INTEGER PRIMARY KEY,valor INTEGER)")
            c.execute("INSERT INTO pedido VALUES(1,2590)")
        before = database.read_bytes()
        with (
            patch.object(setup_geral, "DATA", folder),
            patch.object(
                setup_geral.Config,
                "SQLALCHEMY_DATABASE_URI",
                "sqlite:///" + str(database),
            ),
            patch("builtins.input", side_effect=["Owner", "owner@example.com"]),
            patch(
                "getpass.getpass",
                side_effect=["test-owner-password", "test-owner-password"],
            ),
        ):
            setup_geral.setup()
        self.assertEqual(database.read_bytes(), before)
        legacy = setup_geral.Registry(folder / "plataforma")
        with legacy.connect() as c:
            row = c.execute("SELECT * FROM restaurants").fetchone()
            self.assertEqual(row["slug"], "restaurante-atual")
            self.assertEqual(row["enabled"], 0)


if __name__ == "__main__":
    unittest.main()
