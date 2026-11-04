"""Regressão: pizzas simples começam pelo tamanho e não por um sabor."""
import json
import unittest
import test_product_options as fixture
from models import db, Produto, Categoria, Pedido
from product_options import public_product, size_cards, catalog_products, path_for

class PizzaSizeFirst(unittest.TestCase):
    setUp = fixture.Options.setUp
    tearDown = fixture.Options.tearDown
    login = fixture.Options.login
    post = fixture.Options.post

    def plain_pizzas(self):
        p = db.session.get(Produto, 1)
        p.nome = 'Pizza Calabresa'
        p.descricao = 'Pizza grande de 35 cm, cortada em 8 fatias.'
        other = Produto(nome='Pizza Frango', descricao=p.descricao, preco=6500, categoria_id=1)
        db.session.add(other)
        db.session.commit()
        return p, other

    def test_imported_plain_pizzas_group_by_existing_size_without_writing_options(self):
        p, other = self.plain_pizzas()
        self.assertEqual([p], catalog_products([p, other]))
        config = public_product(p)
        self.assertEqual(size_cards(p)[0]['label'], 'Grande · 8 fatias')
        self.assertEqual(size_cards(p)[0]['from_price'], 5000)
        self.assertEqual([c['price'] for c in config['groups'][1]['choices']], [5000, 6500])
        self.assertFalse(path_for(p.id).exists())
        page = self.client.get('/pdv').get_data(as_text=True)
        self.assertEqual(page.count('class="product catalog-product pizza-size-product"'), 1)
        self.assertIn('Grande · 8 fatias',page)

    def test_server_prices_selected_flavor_and_retains_size_in_snapshot(self):
        p, other = self.plain_pizzas()
        config = public_product(p)
        item = dict(id=p.id, quantidade=1, preco=1, opcoes_versao=config['version'], quantidade_sabores=1,
                    opcoes={'pizzasize':['original'], 'pizzaflavor':['product'+str(other.id)]})
        result=self.post('/api/pedidos', {'comanda':'99','numero_mesa':'1','itens':[item]})
        self.assertEqual(result.status_code,201,result.get_data(as_text=True))
        order=db.session.get(Pedido,result.json['id'])
        self.assertEqual(order.total,6500)
        self.assertEqual(order.itens[0].nome,'Pizza · Grande · 8 fatias')
        self.assertIn('Pizza Frango',order.itens[0].observacao)
        other.ativo=False;db.session.commit()
        rejected=self.post('/api/pedidos', {'comanda':'100','numero_mesa':'1','itens':[item]})
        self.assertEqual(rejected.status_code,409)

    def test_configured_sizes_remain_unchanged_and_identical_config_deduplicates(self):
        p, other = self.plain_pizzas()
        config=public_product(p)
        config['groups'][0]['choices'].append(dict(id='family',label='Família · 16 fatias',price=3000,enabled=True,max_flavors=2))
        saved=dict(groups=config['groups'],notes=config['notes'])
        path_for(p.id).parent.mkdir(parents=True,exist_ok=True)
        for product in [p,other]:path_for(product.id).write_text(json.dumps(saved))
        before=path_for(p.id).read_bytes()
        self.assertEqual(len(size_cards(p)),2)
        self.assertEqual(size_cards(p)[1]['from_price'],8000)
        self.assertEqual(catalog_products([p,other]),[p])
        self.assertEqual(path_for(p.id).read_bytes(),before)

    def test_saving_sizes_on_master_does_not_leave_duplicate_flavor_cards(self):
        p, other = self.plain_pizzas()
        config = public_product(p)
        config['groups'][0]['choices'].append(dict(id='medium',label='Média · 12 fatias',price=2000,enabled=True,max_flavors=2))
        path_for(p.id).parent.mkdir(parents=True,exist_ok=True)
        path_for(p.id).write_text(json.dumps(dict(groups=config['groups'],notes=config['notes'])))
        self.assertEqual(catalog_products([p,other]),[p])
        self.assertEqual(public_product(p)['groups'],public_product(other)['groups'])
        self.assertFalse(path_for(other.id).exists())

    def test_non_pizza_category_unchanged_and_unknown_size_not_invented(self):
        p=db.session.get(Produto,1)
        self.assertEqual(size_cards(p)[0]['label'],'Tamanho único')
        cat=Categoria(nome='Lanches');db.session.add(cat);db.session.flush()
        p.categoria_id=cat.id;db.session.commit()
        self.assertEqual(public_product(p)['groups'],[])
        self.assertEqual(size_cards(p),[])
