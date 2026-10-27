import getpass
from app import app
from models import db, Usuario, Categoria, Produto
from werkzeug.security import generate_password_hash


def seed():
    if not db.session.scalar(db.select(Categoria)):
        for nome, emoji, items in [
            (
                "Hambúrgueres",
                "🍔",
                [
                    ("Burger da casa", "Pão, carne, queijo e salada", 2590),
                    ("Duplo cheddar", "Duas carnes e cheddar cremoso", 3290),
                ],
            ),
            (
                "Pizzas",
                "🍕",
                [
                    ("Margherita", "Molho de tomate, mussarela e manjericão", 4590),
                    ("Calabresa", "Calabresa, cebola e mussarela", 4990),
                ],
            ),
            (
                "Porções",
                "🍟",
                [("Batata crocante", "Porção individual de batatas", 1590)],
            ),
            (
                "Bebidas",
                "🥤",
                [
                    ("Refrigerante lata", "Lata 350 ml", 650),
                    ("Suco natural", "Copo 400 ml", 990),
                ],
            ),
        ]:
            c = Categoria(nome=nome)
            db.session.add(c)
            db.session.flush()
            for n, d, v in items:
                db.session.add(
                    Produto(
                        nome=n, descricao=d, preco=v, emoji=emoji, categoria_id=c.id
                    )
                )
        db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not db.session.scalar(db.select(Usuario).where(Usuario.perfil == "admin")):
            nome = input("Nome do administrador: ").strip() or "Administrador"
            login = input("Login do administrador: ").strip() or "admin"
            senha = getpass.getpass("Crie uma senha (mínimo 10 caracteres): ")
            if len(senha) < 10:
                raise SystemExit("Senha curta. Execute novamente.")
            db.session.add(
                Usuario(
                    nome=nome,
                    login=login,
                    senha=generate_password_hash(senha),
                    perfil="admin",
                )
            )
            db.session.commit()
        seed()
        print("Banco inicializado. Execute: python app.py")
