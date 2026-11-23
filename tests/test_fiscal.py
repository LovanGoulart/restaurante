"""Integração com provedor simulado; não emite notas reais."""

import json, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta
from werkzeug.security import generate_password_hash
from app import create_app
from models import db, Usuario, Item, Pedido, Caixa, Movimento, now
from fiscal_models import ConfiguracoesFiscais, RegraFiscal, FiscalSequencia, NotaFiscal
from fiscal_service import enqueue, encrypt, decrypt, process_one, build_payload
from fiscal_provider import ProviderError, safe_document_url
from fiscal_cli import migrate_current

CNPJ = "11222333000181"
RULE = {
    "codigo_ncm": "21069090",
    "cfop": "5102",
    "unidade": "UN",
    "icms_origem": "0",
    "icms_situacao_tributaria": "102",
    "pis_situacao_tributaria": "07",
    "cofins_situacao_tributaria": "07",
}


class FiscalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "DATA_DIR": self.temp.name,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///"
                + str(Path(self.temp.name) / "test.db"),
            }
        )
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        for role in ["admin", "garcom", "cozinha", "cliente", "entregador"]:
            db.session.add(
                Usuario(
                    nome=role,
                    login=role,
                    senha=generate_password_hash("test-password"),
                    perfil=role,
                )
            )
        db.session.flush()
        config = ConfiguracoesFiscais(
            id=1,
            cnpj=CNPJ,
            razao_social="Teste",
            inscricao_estadual="123",
            regime_tributario="1",
            ambiente="homologacao",
            empresa_api_id="123",
            token_cifrado=encrypt("emitter-test"),
            master_cifrado=encrypt("master-test"),
            parametros={
                "serie": 1,
                "aliquota_icms": "18",
                "pix_codigo": "20",
                "uf": "RS",
            },
            emitir_automaticamente=True,
        )
        db.session.add_all(
            [
                config,
                RegraFiscal(nome_item="Pizza", campos=RULE),
                FiscalSequencia(
                    cnpj=CNPJ, ambiente="homologacao", serie=1, proximo_numero=10
                ),
                Caixa(inicial=0),
            ]
        )
        db.session.commit()
        self.client = self.app.test_client()
        self.login(1)

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.ctx.pop()
        self.temp.cleanup()

    def login(self, uid):
        with self.client.session_transaction() as s:
            s["uid"] = uid
            s["csrf"] = "csrf"
            s["management_grants"] = {"fiscal": time.time() + 300}

    def post(self, path, **kwargs):
        return self.client.post(path, headers={"X-CSRF-Token": "csrf"}, **kwargs)

    def order(self, paid=False):
        p = Pedido(mesa="123", numero_mesa="8", usuario_id=1, pago=paid)
        p.itens = [Item(nome="Pizza", preco=2590, quantidade=2)]
        db.session.add(p)
        db.session.commit()
        return p

    def note(self):
        p = self.order(True)
        n = enqueue(p, "pix")
        db.session.commit()
        return n

    def response(self):
        return 201, {
            "status": "autorizado",
            "chave_nfe": "4" * 44,
            "caminho_danfe": "/notas/a.html",
            "caminho_xml_nota_fiscal": "/notas/a.xml",
            "status_sefaz": "100",
        }

    def config_form(self):
        return {
            "cnpj": CNPJ,
            "ambiente": "homologacao",
            "empresa_api_id": "123",
            "token": "new-emitter",
            "master": "new-master",
            "razao_social": "Empresa teste",
            "inscricao_estadual": "123",
            "regime_tributario": "1",
            "serie": "1",
            "proximo_numero": "10",
            "uf_emitente": "RS",
            "pix_codigo": "20",
        }

    def test_payment_enqueues_atomically_without_network(self):
        p = self.order()
        with patch(
            "fiscal_service.call", side_effect=AssertionError("Rede no pagamento")
        ):
            r = self.post(f"/api/pedidos/{p.id}/pagar", json={"forma": "pix"})
        self.assertEqual(r.status_code, 200)
        note = db.session.scalar(db.select(NotaFiscal))
        self.assertEqual(note.status, "pendente")
        self.assertTrue(db.session.get(Pedido, p.id).pago)
        self.assertEqual(db.session.scalar(db.select(Movimento)).valor, 5180)
        self.assertEqual(
            self.post(f"/fiscal/pedidos/{p.id}/emitir", json={}).status_code, 200
        )
        self.assertEqual(
            db.session.scalar(db.select(db.func.count()).select_from(NotaFiscal)), 1
        )

    def test_authorization_and_snapshot(self):
        note = self.note()
        with patch("fiscal_service.call", return_value=self.response()) as api:
            self.assertTrue(process_one(note.id))
        payload = api.call_args.args[4]
        self.assertEqual(payload["valor_total"], "51.80")
        self.assertEqual(payload["items"][0]["valor_bruto"], "51.80")
        self.assertEqual(payload["formas_pagamento"][0]["forma_pagamento"], "20")
        self.assertEqual(payload["numero"], "10")
        self.assertEqual(note.status, "autorizada")
        self.assertEqual(note.chave_acesso, "4" * 44)
        self.assertEqual(
            note.danfe_url, "https://homologacao.focusnfe.com.br/notas/a.html"
        )
        self.assertNotIn("cnpj_emitente", note.payload)
        self.assertEqual(
            json.loads(decrypt(note.payload["cifrado"]))["valor_total"], "51.80"
        )
        self.assertEqual(
            db.session.scalar(db.select(FiscalSequencia)).proximo_numero, 11
        )

    def test_timeout_never_reposts(self):
        note = self.note()
        with patch("fiscal_service.call", side_effect=ProviderError()):
            process_one(note.id)
        self.assertEqual(note.status, "processando")
        self.assertIsNotNone(note.enviado_em)
        note.proxima_consulta = now() - timedelta(seconds=1)
        db.session.commit()
        with patch("fiscal_service.call", return_value=self.response()) as api:
            process_one(note.id)
        self.assertEqual(api.call_args.args[2], "GET")
        self.assertEqual(note.status, "autorizada")
        self.assertEqual(
            db.session.scalar(db.select(FiscalSequencia)).proximo_numero, 11
        )

    def test_rejection_is_persisted(self):
        note = self.note()
        with patch(
            "fiscal_service.call",
            return_value=(
                201,
                {
                    "status": "erro_autorizacao",
                    "mensagem_sefaz": "CFOP inválido",
                    "status_sefaz": "590",
                },
            ),
        ):
            process_one(note.id)
        self.assertEqual(note.status, "rejeitada")
        self.assertIn("CFOP", note.mensagem)
        with patch("fiscal_service.call") as api:
            self.assertFalse(process_one(note.id))
        api.assert_not_called()

    def test_missing_rule_then_fix_before_send(self):
        db.session.execute(db.delete(RegraFiscal))
        db.session.commit()
        note = self.note()
        with patch("fiscal_service.call") as api:
            process_one(note.id)
        api.assert_not_called()
        self.assertEqual(note.status, "erro_configuracao")
        self.assertIsNone(note.numero)
        db.session.add(RegraFiscal(nome_item="Pizza", campos=RULE))
        db.session.commit()
        self.assertEqual(
            self.post(f"/fiscal/notas/{note.id}/corrigir", json={}).status_code, 200
        )
        with patch("fiscal_service.call", return_value=self.response()):
            process_one(note.id)
        self.assertEqual(note.status, "autorizada")

    def test_permissions_and_csrf(self):
        for uid in [2, 3, 4, 5]:
            self.login(uid)
            for path in [
                "/fiscal/testar",
                "/fiscal/configurar",
                "/fiscal/regras",
                "/fiscal/pedidos/1/emitir",
                "/fiscal/certificado/enviar",
            ]:
                self.assertEqual(self.post(path, json={}).status_code, 403)
        self.login(1)
        self.assertEqual(self.client.post("/fiscal/testar", data={}).status_code, 400)
        with self.client.session_transaction() as s:
            s["management_grants"] = {}
        self.assertEqual(self.post("/fiscal/regras", json={}).status_code, 403)

    def test_connection_before_save_and_redacted_secrets(self):
        form = self.config_form()
        self.assertEqual(self.post("/fiscal/configurar", data=form).status_code, 400)
        with patch(
            "fiscal.call",
            side_effect=[
                (200, {"cnpj": CNPJ, "token_homologacao": "new-emitter"}),
                (404, {"codigo": "nao_encontrado"}),
            ],
        ) as api:
            result = self.post("/fiscal/testar", data=form)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(all(c.args[2] == "GET" for c in api.call_args_list))
        self.assertEqual(
            decrypt(db.session.get(ConfiguracoesFiscais, 1).token_cifrado),
            "emitter-test",
        )
        self.assertEqual(self.post("/fiscal/configurar", data=form).status_code, 200)
        self.assertEqual(
            decrypt(db.session.get(ConfiguracoesFiscais, 1).token_cifrado),
            "new-emitter",
        )
        html = self.client.get("/fiscal").get_data(as_text=True)
        self.assertNotIn("new-emitter", html)
        self.assertNotIn("new-master", html)
        self.assertIn("Notas fiscais NFC-e", html)
        self.assertEqual(
            self.post(
                "/fiscal/configurar", data=dict(form, ambiente="producao")
            ).status_code,
            400,
        )

    def test_bad_auth_cnpj_and_provider_error(self):
        for response in [
            (401, {}),
            (200, {"cnpj": "00000000000000"}),
            (200, {"cnpj": CNPJ, "token_homologacao": "wrong"}),
        ]:
            with patch("fiscal.call", return_value=response):
                self.assertEqual(
                    self.post("/fiscal/testar", data=self.config_form()).status_code,
                    400,
                )
        with patch("fiscal.call", side_effect=ProviderError()):
            self.assertEqual(
                self.post("/fiscal/testar", data=self.config_form()).status_code, 502
            )

    def test_claim_prevents_second_worker(self):
        note = self.note()
        note.trava_id = "other"
        note.trava_ate = now() + timedelta(seconds=50)
        db.session.commit()
        with patch("fiscal_service.call") as api:
            self.assertFalse(process_one(note.id))
        api.assert_not_called()

    def test_links_and_authorization_without_valid_key(self):
        self.assertIsNone(safe_document_url("producao", "javascript:alert(1)"))
        self.assertIsNone(safe_document_url("producao", "https://evil.example/x"))
        note = self.note()
        with patch("fiscal_service.call", return_value=(201, {"status": "autorizado"})):
            process_one(note.id)
        self.assertEqual(note.status, "processando")

    def test_taxes_are_calculated_with_decimal(self):
        note = self.note()
        snap = json.loads(json.dumps(note.snapshot))
        snap["empresa"]["regime_tributario"] = "3"
        snap["itens"][0]["regra"].update(
            icms_situacao_tributaria="00",
            pis_situacao_tributaria="01",
            pis_aliquota_porcentual="1.65",
            cofins_situacao_tributaria="01",
            cofins_aliquota_porcentual="7.6",
        )
        note.snapshot = snap
        item = build_payload(note)["items"][0]
        self.assertEqual(item["icms_valor"], "9.32")
        self.assertEqual(item["pis_valor"], "0.85")
        self.assertEqual(item["cofins_valor"], "3.94")
        snap["empresa"]["regime_tributario"] = "4"
        with self.assertRaises(ValueError):
            build_payload(note)

    def test_delivery_recipient_and_freight(self):
        note = self.note()
        snap = json.loads(json.dumps(note.snapshot))
        snap.update(delivery=True, frete=501, total=5681)
        note.snapshot = snap
        db.session.commit()
        with patch("fiscal_service.call") as api:
            process_one(note.id)
        api.assert_not_called()
        self.assertEqual(note.status, "erro_configuracao")
        data = {
            "nome": "Cliente teste",
            "cpf": "52998224725",
            "logradouro": "Rua de teste",
            "numero": "8",
            "bairro": "Centro",
            "municipio": "Porto Alegre",
            "uf": "RS",
            "cep": "90000000",
        }
        self.assertEqual(
            self.post(f"/fiscal/notas/{note.id}/destinatario", data=data).status_code,
            200,
        )
        payload = build_payload(note)
        self.assertEqual(payload["valor_frete"], "5.01")
        self.assertEqual(payload["valor_produtos"], "51.80")
        self.assertEqual(payload["valor_total"], "56.81")
        self.assertEqual(payload["items"][0]["valor_frete"], "5.01")
        self.assertEqual(payload["presenca_comprador"], "4")
        self.assertNotIn(data["cpf"], note.destinatario_cifrado)

    def test_migration_preserves_orders(self):
        order_id = self.order().id
        for model in [NotaFiscal, FiscalSequencia, RegraFiscal, ConfiguracoesFiscais]:
            model.__table__.drop(db.engine)
        backup = migrate_current()
        self.assertTrue(backup.is_file())
        self.assertIsNotNone(db.session.get(Pedido, order_id))
        self.assertIsNone(migrate_current())

    def test_certificate_invalid_and_valid_encrypted_upload(self):
        from io import BytesIO
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.serialization import pkcs12
        from datetime import datetime, timezone

        form = self.config_form()
        with patch(
            "fiscal.call",
            side_effect=[
                (200, {"cnpj": CNPJ, "token_homologacao": "new-emitter"}),
                (404, {"codigo": "nao_encontrado"}),
            ],
        ):
            self.assertEqual(self.post("/fiscal/testar", data=form).status_code, 200)
        invalid = dict(
            form,
            certificado=(BytesIO(b"not a certificate"), "a.pfx"),
            senha_certificado="invalid",
        )
        self.assertEqual(self.post("/fiscal/configurar", data=invalid).status_code, 400)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, "Certificado de teste")]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(1)
            .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=30))
            .sign(key, hashes.SHA256())
        )
        raw = pkcs12.serialize_key_and_certificates(
            b"test",
            key,
            cert,
            None,
            serialization.BestAvailableEncryption(b"cert-test-password"),
        )
        upload = dict(
            form,
            certificado=(BytesIO(raw), "a.pfx"),
            senha_certificado="cert-test-password",
        )
        self.assertEqual(self.post("/fiscal/configurar", data=upload).status_code, 200)
        config = db.session.get(ConfiguracoesFiscais, 1)
        self.assertNotIn("cert-test-password", config.certificado_senha_cifrada)
        import base64

        self.assertEqual(base64.b64decode(decrypt(config.certificado_cifrado)), raw)
        with patch(
            "fiscal.call", side_effect=[(200, {"cnpj": CNPJ}), (200, {})]
        ) as api:
            self.assertEqual(
                self.post("/fiscal/certificado/enviar", json={}).status_code, 200
            )
        self.assertEqual(api.call_args.args[2], "PUT")
        self.assertTrue(api.call_args.args[4]["certificado_especifico"])

    def test_sql_matches_models_and_preserves_tables(self):
        import sqlite3

        path = Path(self.temp.name) / "sql-test.db"
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE pedido(id INTEGER PRIMARY KEY)")
            connection.execute("INSERT INTO pedido(id) VALUES(8)")
            connection.commit()
            sql = (
                Path(__file__).resolve().parents[1] / "sql/001_modulo_fiscal.sql"
            ).read_text()
            connection.executescript(sql)
            connection.executescript(sql)
            self.assertEqual(
                connection.execute("SELECT id FROM pedido").fetchone()[0], 8
            )
            self.assertIsNotNone(
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='nota_fiscal'"
                ).fetchone()
            )

    def test_production_disabled_by_default(self):
        note = self.note()
        note.ambiente = "producao"
        with self.assertRaisesRegex(ValueError, "Produção bloqueada"):
            build_payload(note)

    def test_cnpj_numeric_and_alphanumeric(self):
        from fiscal_service import valid_cnpj

        self.assertTrue(valid_cnpj(CNPJ))
        self.assertTrue(valid_cnpj("12ABC34501DE35"))
        self.assertFalse(valid_cnpj("12ABC34501DE00"))
        self.assertFalse(valid_cnpj("00000000000000"))

    def test_tenant_isolation(self):
        other = create_app(
            {
                "TESTING": True,
                "DATA_DIR": str(Path(self.temp.name) / "other"),
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )
        with other.app_context():
            db.create_all()
            self.assertIsNone(db.session.get(ConfiguracoesFiscais, 1))
            self.assertEqual(
                db.session.scalar(db.select(db.func.count()).select_from(NotaFiscal)), 0
            )
            db.session.remove()
            db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
