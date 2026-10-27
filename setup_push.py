"""Configuração local de chaves VAPID, sem enviar segredos a terceiros."""

import base64, json, os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from config import DATA


def setup(email):
    path = DATA / "vapid.json"
    if path.exists():
        print("Push já configurado. As chaves existentes foram preservadas.")
        return
    if "@" not in email or any(c.isspace() for c in email):
        raise ValueError("Informe um e-mail de contato válido.")
    key = ec.generate_private_key(ec.SECP256R1())
    private = (
        base64.urlsafe_b64encode(
            key.private_numbers().private_value.to_bytes(32, "big")
        )
        .decode()
        .rstrip("=")
    )
    public = (
        base64.urlsafe_b64encode(
            key.public_key().public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
        )
        .decode()
        .rstrip("=")
    )
    with path.open("x") as f:
        json.dump(
            {
                "private_key": private,
                "public_key": public,
                "subject": "mailto:" + email,
            },
            f,
        )
    path.chmod(0o600)
    print("Push configurado. Reinicie run.py e ative os avisos em cada dispositivo.")


if __name__ == "__main__":
    setup(input("E-mail de contato do responsável pelo sistema: ").strip())
