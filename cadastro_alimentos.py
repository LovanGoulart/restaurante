"""Cadastre o cardápio demonstrativo no Restaurante Manager (SQLite).

Extraia este arquivo e a pasta imagens ao lado de app.py.
Feche o servidor antes de executar: python cadastro_alimentos.py
Banco alternativo: python cadastro_alimentos.py --banco caminho/restaurante.db
Só conferir: python cadastro_alimentos.py --simular
Não altera preços, descrições ou fotos já cadastrados.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import unicodedata
from datetime import datetime

BASE = Path(__file__).resolve().parent
# Categoria, nome, descrição, preço em CENTAVOS, arquivo, emoji.
PRODUTOS = [
    ("Hambúrgueres", "Hambúrguer Clássico", "Pão brioche, hambúrguer bovino de 160 g, queijo muçarela derretido, alface, tomate e maionese da casa.", 2790, "hamburguer_classico.jpg", "🍔"),
    ("Hambúrgueres", "Hambúrguer Bacon Cheddar", "Pão brioche, hambúrguer bovino de 180 g, queijo cheddar, bacon crocante e cebola caramelizada.", 3490, "hamburguer_bacon_cheddar.jpg", "🍔"),
    ("Hambúrgueres", "Hambúrguer Duplo Smash", "Pão brioche, dois hambúrgueres bovinos de 90 g prensados na chapa, cheddar em cada camada, picles e molho especial da casa.", 3690, "hamburguer_duplo_smash.jpg", "🍔"),
    ("Pizzas", "Pizza Calabresa", "Massa artesanal, molho de tomate, muçarela, calabresa fatiada, cebola, azeitonas e orégano. Pizza grande de 35 cm, cortada em 8 fatias.", 5990, "pizza_calabresa.jpg", "🍕"),
    ("Pizzas", "Pizza Frango com Requeijão", "Massa artesanal, molho de tomate, muçarela, frango desfiado temperado, requeijão cremoso, milho e orégano. Pizza grande de 35 cm, cortada em 8 fatias.", 6490, "pizza_frango_requeijao.jpg", "🍕"),
    ("Pizzas", "Pizza Quatro Queijos", "Massa artesanal, molho de tomate, muçarela, provolone, parmesão, gorgonzola e orégano. Pizza grande de 35 cm, cortada em 8 fatias.", 6990, "pizza_quatro_queijos.jpg", "🍕"),
    ("Tábuas", "Tábua de Frios", "Seleção de salame, presunto cru, cubos de muçarela e provolone, azeitonas e torradas. Ideal para compartilhar entre 2 pessoas.", 6990, "tabua_frios.jpg", "🧀"),
    ("Tábuas", "Tábua de Carnes", "Tiras de carne bovina, frango grelhado e linguiça em rodelas, acompanhados de batata frita, farofa e vinagrete. Serve 2 pessoas.", 9490, "tabua_carnes.jpg", "🥩"),
    ("Tábuas", "Tábua de Petiscos", "Frango empanado, palitos de muçarela empanados, anéis de cebola e batata frita. Acompanha maionese da casa e molho barbecue. Serve 2 pessoas.", 7990, "tabua_petiscos.jpg", "🍽️"),
    ("Porções", "Batata Frita", "Porção de batatas fritas douradas e crocantes, levemente salgadas. Acompanha maionese da casa. Serve 2 pessoas como petisco.", 2490, "batata_frita.jpg", "🍟"),
    ("Porções", "Batata com Cheddar e Bacon", "Porção de batatas fritas cobertas com molho cremoso de cheddar e bacon crocante em pedaços. Serve 2 pessoas como petisco.", 3490, "batata_cheddar_bacon.jpg", "🍟"),
    ("Porções", "Iscas de Frango", "Tiras de peito de frango temperadas e empanadas, fritas até ficarem douradas e crocantes. Acompanha limão e maionese de alho. Serve 2 pessoas como petisco.", 3990, "iscas_frango.jpg", "🍗"),
    ("Bebidas", "Água Mineral", "Água mineral sem gás, servida gelada em garrafa individual de 500 ml.", 500, "agua_mineral.jpg", "💧"),
    ("Bebidas", "Refrigerante Cola", "Refrigerante sabor cola, servido gelado em lata de 350 ml.", 700, "refrigerante_cola.jpg", "🥤"),
    ("Bebidas", "Suco de Laranja", "Suco natural de laranja, preparado na hora, sem adição de água ou açúcar. Copo de 400 ml.", 1200, "suco_laranja.jpg", "🍊"),
    ("Drinks", "Caipirinha de Limão", "Drink preparado com cachaça, limão-taiti macerado, açúcar e gelo. Refrescante e com sabor cítrico. Contém álcool.", 2290, "caipirinha_limao.jpg", "🍹"),
    ("Drinks", "Gin Tônica", "Gin, água tônica e gelo, finalizados com uma rodela de limão e um ramo de alecrim. Contém álcool.", 2990, "gin_tonica.jpg", "🍸"),
    ("Drinks", "Mojito", "Rum branco, limão, folhas de hortelã, açúcar, água com gás e gelo. Drink cítrico e refrescante. Contém álcool.", 2690, "mojito.jpg", "🍹"),
]

def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto.casefold())
                   if not unicodedata.combining(c)).strip()

def escolher_banco(explicito):
    if explicito:
        path = Path(explicito).expanduser().resolve()
    else:
        if os.environ.get("DATABASE_URL"):
            raise ValueError("DATABASE_URL está definido. Informe explicitamente --banco com o arquivo SQLite correto.")
        candidatos = sorted((BASE / "instance").rglob("restaurante.db"))
        if not candidatos:
            raise ValueError("Banco não encontrado. Coloque o pacote ao lado de app.py ou use --banco CAMINHO.")
        if len(candidatos) == 1:
            path = candidatos[0]
        else:
            print("Escolha o banco do restaurante que receberá os produtos:")
            for i, candidato in enumerate(candidatos, 1):
                print(f"{i}: {candidato}")
            escolha = int(input("Número: "))
            if not 1 <= escolha <= len(candidatos):
                raise ValueError("Escolha inválida.")
            path = candidatos[escolha - 1]
    if not path.is_file():
        raise ValueError(f"O banco não existe: {path}")
    return path.resolve()

def validar(conn):
    estrutura = {}
    for tabela, obrigatorias in {
        "categoria": {"id", "nome"},
        "produto": {"id", "nome", "descricao", "preco", "emoji", "ativo", "categoria_id"},
    }.items():
        colunas = {r[1]: r for r in conn.execute(f"PRAGMA table_info({tabela})")}
        if not obrigatorias <= colunas.keys():
            raise ValueError(f"Banco incompatível: confira a tabela {tabela}. Nenhum dado alterado.")
        estrutura[tabela] = set(colunas)
        for nome, coluna in colunas.items():
            if nome not in obrigatorias | {"excluido"} and coluna[3] and coluna[4] is None and not coluna[5]:
                raise ValueError(f"Campo obrigatório desconhecido: {tabela}.{nome}")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("O banco apresentou erro de integridade.")
    return estrutura

def importar(banco, pasta_dados, imagens, simular=False):
    # mode=rw impede criar por engano um banco vazio.
    conn = sqlite3.connect(banco.as_uri() + "?mode=rw", uri=True, timeout=10)
    conn.execute("PRAGMA foreign_keys=ON")
    novos_arquivos = []
    alterou_json = False
    temporario = None
    try:
        estrutura = validar(conn)
        arquivo_json = pasta_dados / "appearance.json"
        original = arquivo_json.read_bytes() if arquivo_json.exists() else None
        visual = json.loads(original.decode("utf-8-sig")) if original else {}
        if not isinstance(visual, dict) or not isinstance(visual.get("photos", {}), dict):
            raise ValueError("Formato inválido de appearance.json.")
        visual["photos"] = dict(visual.get("photos", {}))
        for item in PRODUTOS:
            foto = imagens / item[4]
            if not foto.is_file() or foto.read_bytes()[:2] != b"\xff\xd8":
                raise ValueError(f"Imagem JPG ausente ou inválida: {foto}")
        print(f"Banco: {banco}")
        print(f"Fotos e personalização: {pasta_dados}")
        if simular:
            existentes = {normalizar(r[0]) for r in conn.execute("SELECT nome FROM produto")}
            for item in PRODUTOS:
                print(("PRESERVAR" if normalizar(item[1]) in existentes else "CADASTRAR") + ": " + item[1])
            print("Simulação concluída. Nenhum arquivo ou cadastro alterado.")
            return
        # Execute com o servidor parado: banco e JSON são recursos distintos.
        backup = pasta_dados / "backups" / ("cadastro_alimentos_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        backup.mkdir(parents=True)
        with sqlite3.connect(backup / banco.name) as destino:
            conn.backup(destino)
        if original is not None:
            (backup / "appearance.json").write_bytes(original)
        (backup / "LEIA.txt").write_text(
            f"Banco original: {banco}\nPersonalização: {arquivo_json}\n"
            f"appearance.json existia: {original is not None}\n"
            "Para restaurar, pare o servidor e restaure estes arquivos nos caminhos acima.\n",
            encoding="utf-8")
        print(f"Backup: {backup}")
        conn.execute("BEGIN IMMEDIATE")
        categorias = {}
        for cid, nome in conn.execute("SELECT id,nome FROM categoria"):
            categorias.setdefault(normalizar(nome), []).append(cid)
        produtos = {}
        for pid, nome in conn.execute("SELECT id,nome FROM produto"):
            produtos.setdefault(normalizar(nome), []).append(pid)
        inseridos = preservados = fotos = 0
        for categoria, nome, descricao, preco, foto, emoji in PRODUTOS:
            encontrados = produtos.get(normalizar(nome), [])
            if len(encontrados) > 1:
                raise ValueError(f"Há produtos ambíguos com o nome {nome}; resolva a duplicação primeiro.")
            if encontrados:
                pid = encontrados[0]
                preservados += 1
            else:
                ids = categorias.get(normalizar(categoria), [])
                if len(ids) > 1:
                    raise ValueError(f"Categoria ambígua: {categoria}")
                if not ids:
                    cid = conn.execute(
                        "INSERT INTO categoria(nome,excluido) VALUES (?,0)"
                        if "excluido" in estrutura["categoria"]
                        else "INSERT INTO categoria(nome) VALUES (?)",
                        (categoria,)).lastrowid
                    categorias[normalizar(categoria)] = [cid]
                else:
                    cid = ids[0]
                pid = conn.execute(
                    "INSERT INTO produto(nome,descricao,preco,emoji,ativo,categoria_id,excluido) VALUES(?,?,?,?,1,?,0)"
                    if "excluido" in estrutura["produto"]
                    else "INSERT INTO produto(nome,descricao,preco,emoji,ativo,categoria_id) VALUES(?,?,?,?,1,?)",
                    (nome, descricao, preco, emoji, cid)).lastrowid
                produtos[normalizar(nome)] = [pid]
                inseridos += 1
            if not visual["photos"].get(str(pid)):
                raw = (imagens / foto).read_bytes()
                nome_foto = hashlib.sha256(raw).hexdigest()[:32] + ".jpg"
                media = pasta_dados / "media"
                media.mkdir(exist_ok=True)
                destino = media / nome_foto
                if destino.exists():
                    if destino.read_bytes() != raw:
                        raise ValueError(f"Conflito no arquivo {destino}")
                else:
                    with destino.open("xb") as f:
                        f.write(raw)
                    novos_arquivos.append(destino)
                visual["photos"][str(pid)] = nome_foto
                fotos += 1
        if fotos:
            temporario = pasta_dados / ("cadastro-" + os.urandom(8).hex() + ".tmp")
            temporario.write_text(json.dumps(visual, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporario, arquivo_json)
            alterou_json = True
        conn.commit()
        print(f"Concluído: {inseridos} cadastrados, {preservados} preservados, {fotos} fotos vinculadas.")
    except BaseException:
        conn.rollback()
        if alterou_json:
            if original is None:
                arquivo_json.unlink(missing_ok=True)
            else:
                arquivo_json.write_bytes(original)
        for path in novos_arquivos:
            path.unlink(missing_ok=True)
        raise
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
        conn.close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--banco", help="Arquivo SQLite do restaurante (deve existir).")
    parser.add_argument("--pasta-dados", help="DATA_DIR do restaurante; padrão: pasta do banco.")
    parser.add_argument("--imagens", default=str(BASE / "imagens"))
    parser.add_argument("--simular", action="store_true")
    args = parser.parse_args()
    try:
        banco = escolher_banco(args.banco)
        dados = Path(args.pasta_dados).resolve() if args.pasta_dados else banco.parent
        if not dados.is_dir():
            raise ValueError("A pasta de dados não existe.")
        importar(banco, dados, Path(args.imagens).resolve(), args.simular)
        return 0
    except (ValueError, OSError, sqlite3.Error, EOFError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
