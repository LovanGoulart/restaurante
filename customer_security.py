"""Validação local dos dígitos do CPF; não consulta situação ou titularidade."""

import hashlib, hmac, re
from datetime import date, datetime, timezone, timedelta
from cryptography.fernet import Fernet
from flask import abort, request
from models import db, TentativaAcesso
from config import DATA


def cpf_valido(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9.\-\s]+", value):
        return False
    n = re.sub(r"\D", "", value)
    if len(n) != 11 or len(set(n)) == 1:
        return False
    for size in [9, 10]:
        digit = (sum(int(n[i]) * (size + 1 - i) for i in range(size)) * 10) % 11
        if int(n[size]) != (0 if digit == 10 else digit):
            return False
    return True


def cpf_digits(value):
    return re.sub(r"\D", "", value)


def data_nascimento(value):
    try:
        d = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("Informe uma data de nascimento válida.")
    if d < date(1900, 1, 1) or d > date.today():
        raise ValueError("Informe uma data de nascimento válida.")
    return d


def data_key():
    path = DATA / "customer-data.key"
    if not path.exists():
        # Se já há clientes, a ausência da chave deve ser recuperada do backup.
        from models import Cliente

        if db.session.scalar(db.select(Cliente.id).limit(1)):
            raise RuntimeError(
                "Chave de dados ausente. Restaure customer-data.key do backup."
            )
        try:
            with path.open("xb") as f:
                f.write(Fernet.generate_key())
            path.chmod(0o600)
        except FileExistsError:
            pass
    return path.read_bytes().strip()


def encode_cpf(cpf):
    key = data_key()
    return (
        Fernet(key).encrypt(cpf.encode()).decode(),
        hmac.new(key, cpf.encode(), hashlib.sha256).hexdigest(),
    )


def throttle(scope, limit, seconds):
    # IP vem da conexão; não confiar diretamente em X-Forwarded-For.
    raw = scope + "|" + (request.remote_addr or "local")
    key = hashlib.sha256(raw.encode()).hexdigest()
    cut = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    count = db.session.scalar(
        db.select(db.func.count())
        .select_from(TentativaAcesso)
        .where(TentativaAcesso.chave == key, TentativaAcesso.criado >= cut)
    )
    if count >= limit:
        abort(429, "Muitas tentativas. Aguarde alguns minutos e tente novamente.")
    db.session.add(TentativaAcesso(chave=key))
    db.session.execute(
        db.delete(TentativaAcesso).where(
            TentativaAcesso.criado < datetime.now(timezone.utc) - timedelta(days=1)
        )
    )
    db.session.commit()
