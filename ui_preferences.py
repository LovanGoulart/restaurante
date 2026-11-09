"""Browser preferences and translations for Manager's interface."""
import json
import re
from pathlib import Path

from flask import has_request_context, request
from jinja2.ext import Extension

LANGUAGES = {"pt-BR", "en", "es"}
CATALOG = json.loads(
    (Path(__file__).parent / "static" / "ui-translations.json").read_text(encoding="utf-8")
)
TOKENS = re.compile(
    r'{%.*?%}|{{.*?}}|{#.*?#}|<!--.*?-->|<(script|style)\b[^>]*>.*?</\1>'
    r'|<(?:[^>"\x27]|"[^"]*"|\x27[^\x27]*\x27)*>|[^<{]+|.',
    re.S | re.I,
)
DISPLAY_OUTPUTS = {
    "_catalog_products.html": {
        "size.label": "ui_size",
        "'opção' if card_count.value == 1 else 'opções'": "ui_text",
        "'sabor' if size.limit==1 else 'sabores'": "ui_text",
    },
    "personalizacao.html": {"'Trocar foto' if photo else 'Adicionar foto'": "ui_text"},
    "pizza_settings.html": {"size.label": "ui_text"},
    "pedidos.html": {"'Acompanhe seu pedido.' if customer else 'Pedidos'": "ui_text"},
}
ATTRIBUTES = re.compile(r'\b(?:aria-label|placeholder|title|alt)=(["\x27])([^"\x27{}]+)\1')


def ui_language():
    if not has_request_context():
        return "pt-BR"
    language = request.cookies.get("manager_language", "pt-BR")
    return language if language in LANGUAGES else "pt-BR"


def ui_theme():
    return "dark" if has_request_context() and request.cookies.get("manager_theme") == "dark" else "light"


def ui_text(text):
    language = ui_language()
    translated = CATALOG.get(" ".join(text.split())) if isinstance(text, str) else None
    return translated.get(language, text) if translated else text


def ui_size(label):
    match = re.fullmatch(r"(.+?) · (\d+) fatias", label)
    if not match:
        return label
    return f"{ui_text(match[1])} · {match[2]} {ui_text('fatias')}"


def ui_catalog():
    language = ui_language()
    return {source: values[language] for source, values in CATALOG.items() if language in values}


class InterfaceTranslation(Extension):
    """Mark literal UI copy in HTML templates before Jinja compiles them.

    Template expressions remain intact, including names, notes and prices
    supplied by the restaurant. Only complete catalog matches are marked.
    """

    def preprocess(self, source, name, filename=None):
        if not name or not name.endswith(".html"):
            return source

        def expression(text):
            normalized = " ".join(text.split())
            if normalized not in CATALOG:
                return text
            leading = text[:len(text) - len(text.lstrip())]
            trailing = text[len(text.rstrip()):]
            literal = json.dumps(normalized, ensure_ascii=False)
            return f"{leading}{{{{ ui_text({literal}) }}}}{trailing}"

        def translate_token(match):
            token = match[0]
            if token.startswith(("{", "<!--")) or match[1]:
                return token
            if token.startswith("<"):
                return ATTRIBUTES.sub(
                    lambda attr: attr[0][:attr.start(2) - attr.start(0)]
                    + expression(attr[2]) + attr[1],
                    token,
                )
            return expression(token)

        result = TOKENS.sub(translate_token, source)
        displays = {"error": "ui_text", "message": "ui_text", **DISPLAY_OUTPUTS.get(name, {})}
        for value, translator in displays.items():
            result = re.sub(r"{{\s*" + re.escape(value) + r"\s*}}",
                            f"{{{{ {translator}({value}) }}}}", result)
        return result


def init_ui_preferences(app):
    app.jinja_env.add_extension(InterfaceTranslation)
    app.jinja_env.globals.update(
        ui_language=ui_language, ui_theme=ui_theme, ui_text=ui_text, ui_catalog=ui_catalog, ui_size=ui_size,
    )
