"""Falhas no salvamento e renovação da senha sem descartar a edição."""

import time
import unittest
from unittest.mock import patch
import test_product_options as fixtures
from product_options import path_for, settings


class OptionsSave(unittest.TestCase):
    setUp = fixtures.Options.setUp
    tearDown = fixtures.Options.tearDown
    login = fixtures.Options.login
    post = fixtures.Options.post
    config = fixtures.Options.config

    def test_manually_locked_area_can_be_renewed_before_payload_is_saved(self):
        payload = self.config()
        with self.client.session_transaction() as session:
            session["management_grants"] = {}
        denied = self.post("/cadastros/produtos/1/opcoes", payload)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json["code"], "management_auth_required")
        bad = self.post(
            "/acesso-restrito", {"destino": "/cadastros/produtos", "senha": "wrong"}
        )
        self.assertEqual(bad.status_code, 403)
        self.assertIn("Senha incorreta", bad.json["error"])
        renewed = self.post(
            "/acesso-restrito",
            {"destino": "/cadastros/produtos", "senha": "test-password"},
        )
        self.assertEqual(renewed.status_code, 200)
        self.assertTrue(renewed.json["ok"])
        result = self.post("/cadastros/produtos/1/opcoes", payload)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(settings(1)["groups"][0]["title"], "Tamanho e fatias")

    def test_validation_and_conflict_are_json(self):
        payload = self.config()
        payload["groups"][0]["title"] = ""
        result = self.post("/cadastros/produtos/1/opcoes", payload)
        self.assertEqual(result.status_code, 400)
        self.assertIn("Preencha", result.json["error"])
        result = self.post(
            "/cadastros/produtos/1/opcoes", dict(self.config(), version="old")
        )
        self.assertEqual(result.status_code, 409)
        self.assertIn("outra tela", result.json["error"])

    def test_csrf_is_json_and_no_password_bypass(self):
        result = self.client.post("/cadastros/produtos/1/opcoes", json=self.config())
        self.assertEqual(result.status_code, 400)
        self.assertIn("Sessão expirada", result.json["error"])
        for uid in [2, 3]:
            self.login(uid)
            self.assertEqual(
                self.post(
                    "/acesso-restrito",
                    {"destino": "/cadastros/produtos", "senha": "test-password"},
                ).status_code,
                403,
            )
            self.assertEqual(
                self.post("/cadastros/produtos/1/opcoes", self.config()).status_code,
                403,
            )

    def test_file_failure_returns_useful_message_and_preserves_config(self):
        self.assertEqual(
            self.post("/cadastros/produtos/1/opcoes", self.config()).status_code, 200
        )
        original = path_for(1).read_bytes()
        payload = self.config()
        payload["groups"][0]["title"] = "Alterado"
        with patch("product_options.os.replace", side_effect=PermissionError("denied")):
            result = self.post("/cadastros/produtos/1/opcoes", payload)
        self.assertEqual(result.status_code, 503)
        self.assertIn("permissão", result.json["error"])
        self.assertEqual(path_for(1).read_bytes(), original)
        self.assertEqual(list(path_for(1).parent.glob("*.tmp")), [])

    def test_invalid_json_config_is_reported_without_overwriting(self):
        path_for(1).parent.mkdir()
        path_for(1).write_text("{broken")
        result = self.post("/cadastros/produtos/1/opcoes", {})
        self.assertEqual(result.status_code, 503)
        self.assertIn("ler a configuração", result.json["error"])
        self.assertEqual(path_for(1).read_text(), "{broken")

    def test_tenant_prefix_and_destination_validation(self):
        result = self.client.post(
            "/acesso-restrito",
            json={"destino": "/r/kasarao/cadastros/produtos", "senha": "test-password"},
            headers={"X-CSRF-Token": "token"},
            environ_overrides={"SCRIPT_NAME": "/r/kasarao"},
        )
        self.assertEqual(result.status_code, 200)
        result = self.post(
            "/acesso-restrito",
            {"destino": "https://evil.example", "senha": "test-password"},
        )
        self.assertEqual(result.status_code, 400)
        self.assertIsNotNone(result.json)


if __name__ == "__main__":
    unittest.main()
