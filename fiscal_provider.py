"""Adaptador Focus NFe v2. URLs fixas, TLS, sem redirects/retry de POST."""

import base64
import json
import socket
import ssl
from urllib import request, error, parse

HOSTS = {
    "homologacao": "https://homologacao.focusnfe.com.br",
    "producao": "https://api.focusnfe.com.br",
}


class ProviderError(Exception):
    def __init__(self, code=0):
        self.code = code
        super().__init__(
            f"Falha na comunicação fiscal (HTTP {code or 'indisponível'})."
        )


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def call(ambiente, token, method, path, body=None):
    if ambiente not in HOSTS or not token or not path.startswith("/v2/"):
        raise ValueError("Ambiente ou credencial fiscal inválidos.")
    auth = base64.b64encode((token + ":").encode()).decode()
    req = request.Request(
        HOSTS[ambiente] + path,
        data=json.dumps(body, allow_nan=False).encode() if body is not None else None,
        method=method,
        headers={
            "Authorization": "Basic " + auth,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    opener = request.build_opener(
        NoRedirect(), request.HTTPSHandler(context=ssl.create_default_context())
    )
    try:
        with opener.open(req, timeout=20) as response:
            code, raw = response.status, response.read(2 * 1024 * 1024 + 1)
    except error.HTTPError as exc:
        code, raw = exc.code, exc.read(2 * 1024 * 1024 + 1)
    except (error.URLError, TimeoutError, socket.timeout, OSError):
        raise ProviderError() from None
    try:
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError()
    except (ValueError, UnicodeError):
        raise ProviderError(code) from None
    return code, data


def safe_document_url(ambiente, value):
    if not isinstance(value, str) or not value:
        return None
    url = parse.urljoin(HOSTS[ambiente] + "/", value)
    parts = parse.urlsplit(url)
    # Nunca permitir javascript:, URLs de terceiros ou credenciais em links.
    if (
        parts.scheme != "https"
        or parts.netloc != parse.urlsplit(HOSTS[ambiente]).netloc
    ):
        return None
    return url


def nfce_path(ref):
    return "/v2/nfce/" + parse.quote(ref, safe="")
