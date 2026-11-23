"""Uma configuração de tamanhos por categoria; sabores são produtos reais."""
import hashlib
import json
import os
import re
import secrets
from copy import deepcopy
from pathlib import Path
from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, url_for
from config import DATA, data_dir
from models import db, Categoria, Produto
from werkzeug.exceptions import HTTPException

bp = Blueprint('pizza_menu', __name__)

@bp.errorhandler(HTTPException)
def json_error(error):
    db.session.rollback()
    if request.is_json:return jsonify(error=error.description),error.code
    return render_template('error.html',message=error.description),error.code

SLOTS = [('broto','Broto',4,1),('media','Pizza média',8,2),('grande','Pizza grande',12,4),('familia','Pizza família',16,6)]


def normalized(value):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))


def is_category(category):
    return bool(category and not category.excluido and 'pizza' in normalized(category.nome))


def applies(product):
    return is_category(db.session.get(Categoria,product.categoria_id))


def path_for(category_id):
    return data_dir(DATA)/'pizza-menus'/f'{int(category_id)}.json'


def products_for(category_id, active=True):
    query=db.select(Produto).where(Produto.categoria_id==category_id,Produto.excluido.is_(False)).order_by(Produto.id)
    if active: query=query.where(Produto.ativo.is_(True))
    return db.session.scalars(query).all()


def defaults(category_id):
    sizes=[dict(id=id,label=label,slices=slices,max_flavors=limit,amount=0,enabled=True) for id,label,slices,limit in SLOTS]
    notes=dict(enabled=True,label='Observação',placeholder='Ex.: sem cebola')
    modifiers=[dict(id='massas',title='Massas',type='single',enabled=True,required=True,max=1,choices=[dict(id='tradicional',label='Tradicional',description='',price=0,enabled=True),dict(id='fina',label='Fina',description='',price=0,enabled=True)]),dict(id='bordas',title='Bordas',type='single',enabled=False,required=False,max=1,choices=[]),dict(id='acompanhamentos',title='Acompanhamentos',type='multiple',enabled=False,required=False,max=2,choices=[])]
    # Aproveitar o primeiro conjunto legado, sem gravar nem alterar os arquivos antigos.
    for product in products_for(category_id,False):
        old=data_dir(DATA)/'product-options'/f'{product.id}.json'
        if not old.exists(): continue
        legacy=json.loads(old.read_text(encoding='utf-8'))
        size_group=next((group for group in legacy.get('groups',[]) if group.get('type')=='sizes'),None)
        if not size_group: continue
        for choice in size_group.get('choices',[]):
            label=normalized(choice['label'])
            slot=next((size for size in sizes if re.search(r'\b'+size['id']+r'\b',label)),None)
            if slot:
                slices=re.search(r'(\d+)\s*fatias',label)
                slot.update(amount=choice['price'],max_flavors=choice.get('max_flavors',1),enabled=bool(size_group.get('enabled') and choice.get('enabled')))
                if slices:slot['slices']=int(slices.group(1))
        extras=[deepcopy(group) for group in legacy.get('groups',[]) if group.get('type') not in {'sizes','flavors'}]
        if extras:
            modifiers=extras
            if not any('massa' in normalized(group['title']) for group in modifiers):modifiers.insert(0,defaults_mass())
        notes=legacy.get('notes',notes)
        break
    return dict(pricing_mode='average',sizes=sizes,modifiers=modifiers,notes=notes)


def defaults_mass():
    return dict(id='massas',title='Massas',type='single',enabled=True,required=True,max=1,choices=[dict(id='tradicional',label='Tradicional',description='',price=0,enabled=True),dict(id='fina',label='Fina',description='',price=0,enabled=True)])


def settings(category_id):
    path=path_for(category_id)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else defaults(category_id)


def revision(config):
    return hashlib.sha256(json.dumps(config,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]


def ordering_modifiers(modifiers):
    """Acompanhamentos da pizza são opcionais e permitem todas as escolhas."""
    result = deepcopy(modifiers)
    for group in result:
        title = normalized(group.get('title', ''))
        if group.get('type') in {'single', 'multiple'} and (
            'acompanh' in title or 'adicion' in title
            or group.get('id') == 'acompanhamentos'
        ):
            group.update(type='multiple', required=False,
                         max=max(1, sum(bool(c.get('enabled')) for c in group['choices'])))
    return result


def effective(product):
    config=settings(product.categoria_id)
    from appearance import settings as appearance_settings
    photos=appearance_settings()['photos']
    flavors=[dict(id='product'+str(p.id),label=p.nome,description=(p.descricao or '')[:400],price=p.preco,enabled=True,photo=photos.get(str(p.id),'')) for p in products_for(product.categoria_id)]
    return dict(pizza_menu=True,pricing_mode=config['pricing_mode'],notes=config['notes'],groups=[dict(id='pizzasize',title='Tamanho e fatias',type='sizes',enabled=True,required=True,max=1,choices=[dict(id=s['id'],label=f"{s['label']} · {s['slices']} fatias",price=s['amount'],slices=s['slices'],max_flavors=s['max_flavors'],enabled=s['enabled']) for s in config['sizes']]),*ordering_modifiers(config['modifiers']),dict(id='pizzaflavor',title='Sabores',type='flavors',enabled=True,required=True,max=20,choices=flavors)])


def clean(data):
    if not isinstance(data,dict) or data.get('pricing_mode') not in {'average','fixed'}:abort(400,'Escolha a forma de definir o preço da pizza.')
    sizes=data.get('sizes')
    if not isinstance(sizes,list) or len(sizes)!=4 or not all(isinstance(s,dict) and isinstance(s.get('id'),str) for s in sizes) or {s['id'] for s in sizes}!={s[0] for s in SLOTS}:abort(400,'Configure os quatro tamanhos: broto, média, grande e família.')
    cleaned=[]
    for id,label,_,_ in SLOTS:
        s=next(s for s in sizes if s['id']==id)
        if type(s.get('enabled')) is not bool or type(s.get('slices')) is not int or not 1<=s['slices']<=100 or type(s.get('max_flavors')) is not int or not 1<=s['max_flavors']<=20 or type(s.get('amount')) is not int or not 0<=s['amount']<=100000000:abort(400,f'Confira o preço, as fatias e o limite de sabores de {label}.')
        cleaned.append(dict(id=id,label=label,slices=s['slices'],max_flavors=s['max_flavors'],amount=s['amount'],enabled=s['enabled']))
    mods=data.get('modifiers')
    if not isinstance(mods,list) or any(not isinstance(group,dict) or group.get('type') not in {'single','multiple','text'} for group in mods):abort(400,'Modificador de pizza inválido.')
    from product_options import clean_config
    legacy=clean_config(dict(groups=mods,notes=data.get('notes')))
    if len(legacy['groups'])>6:abort(400,'Use até seis blocos de massa, borda e acompanhamentos.')
    # Os IDs centrais são reservados e não podem colidir com complementos.
    if any(group['id'] in {'pizzasize','pizzaflavor'} for group in legacy['groups']):abort(400,'Identificador reservado para os tamanhos ou sabores.')
    return dict(pricing_mode=data['pricing_mode'],sizes=cleaned,modifiers=legacy['groups'],notes=legacy['notes'])


def pending_legacy_flavors(category_id):
    def key(name):return re.sub(r'[^a-z0-9]','',re.sub(r'^pizza\s+','',normalized(name)))
    existing={key(p.nome) for p in products_for(category_id,False)}
    pending=[]
    for product in products_for(category_id,False):
        path=data_dir(DATA)/'product-options'/f'{product.id}.json'
        if not path.exists():continue
        for group in json.loads(path.read_text(encoding='utf-8')).get('groups',[]):
            if group.get('type')!='flavors':continue
            for choice in group.get('choices',[]):
                name=choice.get('label','').strip();price=choice.get('price')
                if not name or len(name)>80 or key(name) in existing or type(price) is not int or not 0<=price<=100000000:continue
                existing.add(key(name))
                pending.append(dict(name=name,description=str(choice.get('description',''))[:500],price=price,active=bool(group.get('enabled') and choice.get('enabled'))))
    return pending


@bp.post('/cadastros/produtos/pizzas/importar')
def import_legacy():
    if not g.user or g.user.perfil!='admin':abort(403)
    category=db.get_or_404(Categoria,request.args.get('categoria',type=int))
    if not is_category(category):abort(400,'Categoria de pizzas inválida.')
    category_id=category.id
    db.session.rollback();db.session.execute(db.text('BEGIN IMMEDIATE'))
    pending=pending_legacy_flavors(category_id)
    for flavor in pending:db.session.add(Produto(nome=flavor['name'],descricao=flavor['description'],preco=flavor['price'],ativo=flavor['active'],categoria_id=category_id,emoji='🍕'))
    db.session.commit()
    return jsonify(ok=True,imported=len(pending))


@bp.route('/cadastros/produtos/pizzas',methods=['GET','POST'])
def configure():
    if not g.user:
        if request.is_json:return jsonify(error='Entre novamente no sistema.'),401
        return redirect(url_for('login'))
    if g.user.perfil!='admin':abort(403)
    categories=[c for c in db.session.scalars(db.select(Categoria).order_by(Categoria.id)).all() if is_category(c)]
    category_id=request.args.get('categoria',type=int) or (categories[0].id if categories else None)
    category=next((c for c in categories if c.id==category_id),None)
    if category_id and not category:abort(404)
    config=settings(category.id) if category else None
    if request.method=='POST':
        if not category:abort(400,'Cadastre uma categoria de pizzas primeiro.')
        data=request.get_json(silent=True)
        if not isinstance(data,dict):abort(400,'Envie uma configuração válida.')
        if data.get('version')!=revision(config):abort(409,'As configurações mudaram em outra tela. Reabra antes de salvar.')
        config=clean(data)
        path=path_for(category.id);path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.stem+'-'+secrets.token_hex(8)+'.tmp')
        try:
            with temporary.open('w',encoding='utf-8') as f:json.dump(config,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
            os.replace(temporary,path)
        except OSError:abort(503,'Não foi possível gravar as configurações de pizzas. Confira as permissões da pasta do restaurante.')
        finally:temporary.unlink(missing_ok=True)
        return jsonify(ok=True,version=revision(config))
    return render_template('pizza_settings.html',categories=categories,category=category,config=config,version=revision(config) if config else '',flavors=products_for(category.id,False) if category else [],pending=pending_legacy_flavors(category.id) if category else [])


@bp.app_context_processor
def pizza_art_context():
    return dict(pizza_wheel=pizza_wheel)


def pizza_wheel(slices):
    from math import sin, cos, pi
    from markupsafe import Markup
    slices=max(1,min(100,int(slices or 8)))
    lines=''.join(f'<path d="M50 50 L{50+38*cos(2*pi*i/slices):.2f} {50+38*sin(2*pi*i/slices):.2f}"/>' for i in range(slices))
    toppings=''.join(f'<circle cx="{x}" cy="{y}" r="4"/>' for x,y in [(35,30),(61,29),(72,47),(60,68),(35,69),(27,48)])
    return Markup(f'<svg class="pizza-wheel" viewBox="0 0 100 100" role="img" aria-label="Pizza inteira com {slices} fatias"><circle cx="50" cy="50" r="47" fill="#e9ae61"/><circle cx="50" cy="50" r="40" fill="#f8d36d"/><g fill="#cf6041">{toppings}</g><g fill="#80a058"><ellipse cx="45" cy="37" rx="2" ry="4"/><ellipse cx="65" cy="55" rx="2" ry="4"/><ellipse cx="43" cy="76" rx="2" ry="4"/></g><g class="pizza-cuts" fill="none" stroke="#d69c50" stroke-width="1.5">{lines}</g></svg>')
