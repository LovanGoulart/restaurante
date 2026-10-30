> **Cardápio e opções de produtos:** para esta atualização, leia primeiro [ATUALIZACAO_CARDAPIO_OPCOES.md](ATUALIZACAO_CARDAPIO_OPCOES.md). Não é necessária alteração no banco para a nova tela de opções.

> **Instruções atualizadas:** consulte primeiro [ATUALIZACAO_ACESSOS_E_COMANDAS.md](ATUALIZACAO_ACESSOS_E_COMANDAS.md). Nesta versão o login geral e o login dos administradores do caixa usam e-mail, e a atualização de bancos requer `python atualizar_sistema.py`.

# Administrador geral e restaurantes separados

Esta versão usa o ZIP enviado em 30/10/2026 como base. O acesso geral foi adicionado
sem substituir os layouts e fluxos atuais por outro sistema.

## O que você controla

- Conta única de proprietário, separada das contas dos restaurantes.
- Cadastro de restaurantes, com nome, endereço próprio, login, senha e e-mail do administrador.
- Planos de 1 mês, 3 meses, 6 meses ou 1 ano.
- Renovação, suspensão e reativação manual dos acessos.
- Cadastro de outros administradores no mesmo restaurante, com e-mail obrigatório.
- Ativação/desativação de contas administrativas e redefinição de senha.
- Histórico das últimas alterações de acesso.

Cada restaurante tem seu banco SQLite, imagens, identidade visual, clientes, equipe,
pedidos, caixa e arquivos de segurança separados. É possível usar o mesmo login
em restaurantes diferentes. Clientes usam o cardápio do restaurante escolhido.

O plano pertence ao restaurante. Seus administradores, funcionários e clientes
seguem a validade desse restaurante. Administradores adicionais do mesmo restaurante
compartilham esse prazo, mas você pode desativar cada conta separadamente.

Quando o prazo termina, a situação efetiva passa a Inativo e as próximas requisições
são bloqueadas, inclusive com sessões já abertas. Não depende de agendador ou cron.
Somente o proprietário pode renovar ou reativar. Dados não são apagados por vencimento.

## Atualizar uma instalação que já tem dados

1. Pare o servidor e o worker antes de copiar os arquivos.
2. Faça uma cópia de segurança da pasta inteira do sistema, principalmente `instance`.
3. Extraia este ZIP em uma pasta temporária e copie o código para a sua pasta atual.
   Preserve a pasta `instance` inteira e as variáveis de ambiente da hospedagem.
4. No terminal, entre na pasta que contém `app.py` e ative seu ambiente virtual.
5. Instale/confira as dependências:

```bash
python -m pip install -r requirements.txt
```

6. Configure sua conta de administrador geral pelo terminal:

```bash
python setup_geral.py
```

O script pede seu nome, login, e-mail e senha de pelo menos 12 caracteres, com
confirmação. Não existe senha padrão. Senhas são armazenadas com hash.

Se o banco configurado já contém administradores, ele será registrado no painel
como **Restaurante atual**, no endereço `/r/restaurante-atual/`. A adoção não altera
os pedidos, senhas, clientes ou pagamentos do banco existente, nem move suas chaves
e imagens. Esse restaurante inicia sem plano e inativo para que você determine o prazo.

7. Inicie o sistema:

```bash
python run.py
```

Por padrão, abra `http://127.0.0.1:5000/geral/login`.
O arquivo `app.py` continua disponível para testes locais, na porta 8000.

8. Entre no painel geral. Em Restaurante atual, abra **Administradores** e cadastre
   o e-mail de cada administrador existente. Contas administrativas sem e-mail
   cadastrado pelo proprietário ficam bloqueadas até você completar o contato.
9. Volte ao painel e clique em **Renovar e ativar**, escolhendo o prazo.
10. Compartilhe os novos endereços de login e cardápio desse restaurante.

**Não execute init_db.py para atualizar esta instalação e não apague o banco.**
Não é necessário adicionar colunas ou recriar tabelas do banco antigo nesta etapa.
O controle geral usa um banco novo, separado.

## Instalação nova, sem dados anteriores

Instale as dependências, execute `python setup_geral.py` e depois `python run.py`.
Cadastre os restaurantes pelo painel geral. O cadastro cria automaticamente um banco
vazio para cada restaurante e a conta administrativa informada. O administrador
do restaurante cadastra cardápio, categorias e equipe normalmente.

## Endereços

```text
/geral/login                  Seu login de proprietário
/geral                        Seu painel geral
/r/nome-do-restaurante/login  Login da equipe e administração do restaurante
/r/nome-do-restaurante/cardapio  Cardápio público para os clientes
```

Os links aparecem nos cards do painel. Cada endereço identifica o restaurante;
a raiz do domínio agora é da administração geral. Links antigos como `/pedidos`
ou `/cardapio` precisam ser substituídos pelos links com `/r/.../`.

## Renovação e validade

- O cadastro libera acesso imediatamente pelo período escolhido.
- Datas são apresentadas no horário de Brasília.
- Mês significa mês de calendário, não 30 dias fixos. No fim do mês, ajusta-se ao
  último dia existente do mês de destino (ex.: 31/01 para 28/02 ou 29/02).
- Plano ainda vigente: renovar soma o período ao vencimento atual.
- Plano vencido: renovar conta a partir do momento da renovação.
- Suspender bloqueia imediatamente as próximas requisições.
- Reativar plano vigente libera uma suspensão sem somar tempo. Se vencido, é preciso renovar.
- Desativar uma conta administrativa bloqueia essa conta; não exclui o restaurante.
- Redefinir a senha ou desativar uma conta invalida as sessões anteriores desse administrador.

Não há cobrança, pagamento online ou renovação automática nesta etapa. Você confirma
o recebimento do plano por fora do sistema e libera o período no painel geral.

## E-mails

O e-mail é obrigatório para o proprietário e cada administrador. É validado no servidor
quanto ao formato e tamanho, além da validação do navegador. Não é enviado e-mail
de confirmação, não há recuperação de senha por e-mail e não é verificada a existência
da caixa postal. O contato fica salvo no controle geral, sem exposição ao público.

## Equipe e permissões

Administradores dos restaurantes continuam gerenciando produtos, categorias, equipe,
caixa, clientes e relatórios dentro de seu restaurante. Eles podem cadastrar e ativar
garçons, cozinha e entregadores, mas não podem criar, editar, promover ou reativar
administradores. Essas ações são exclusivas do proprietário.

Também foi corrigido um filtro invertido já presente no ZIP: o garçom agora recebe
somente os pedidos do salão abertos, em preparo e prontos, conforme sua regra anterior.

## Arquivos persistentes e backup

```text
instance/
  restaurante.db                  Banco original, caso já existisse
  secret.key                      Chave original de sessão
  customer-data.key               Chave original dos clientes
  appearance.json                 Personalização original
  media/                          Fotos originais
  vapid.json                      Push original, se já configurado
  plataforma/
    plataforma.db                 Proprietário, restaurantes, contatos e planos
    secret.key                    Chave de sessão do proprietário
    restaurantes/
      identificador-do-restaurante/
        restaurante.db
        secret.key
        customer-data.key         Criada ao cadastrar clientes
        appearance.json           Criada ao personalizar
        media/                    Criada ao enviar fotos
        vapid.json
```

Faça backup da pasta `instance` inteira. O ZIP entregue não contém bancos, chaves,
senhas de produção ou dados dos seus clientes. Ao trocar o código, nunca substitua
uma pasta `instance` preenchida por outra vazia.

Os dados novos são localizados dentro de `instance/plataforma`. Ao migrar para outra
máquina, copie toda a pasta instance e configure o caminho do banco original por
DATABASE_URL, caso ele estivesse fora da pasta padrão.

## PythonAnywhere

O WSGI continua importando a aplicação da mesma forma:

```python
import sys
project_dir = "/home/SEU_USUARIO/restaurante"
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)
from app import app as application
```

Execute `python setup_geral.py` no console do mesmo ambiente virtual usado pela Web.
Depois clique em Reload. O painel fica em `https://SEU_DOMINIO/geral/login`.

Use HTTPS e `COOKIE_SECURE=1` na hospedagem. A configuração de caminho do banco
original foi preservada. Não mapeie a pasta `instance` como arquivo estático público.
As rotas `/r/.../` são atendidas pela aplicação WSGI; não precisam de subdomínios.

Para Web Push, mantenha um processo separado supervisionado:

```bash
python push_worker.py
```

O worker percorre os restaurantes ativos e envia apenas as notificações do respectivo
banco. Novos restaurantes recebem chaves VAPID próprias, usando seu e-mail de contato;
isso não envia e-mails. A hospedagem precisa permitir manter esse processo ativo.
Na execução local, `run.py` já inicia o worker.

## PWA

Cada restaurante agora tem manifesto, sessão, carrinho e service worker com seu próprio
escopo `/r/.../`. Abra o link do restaurante e instale por ele. Se havia um aplicativo
instalado pela raiz antiga, remova-o e reinstale pelo novo link. O worker antigo da
raiz é retirado na atualização; os workers dos restaurantes são preservados.

## Redefinir seu acesso geral

Somente no terminal do servidor:

```bash
python setup_geral.py --redefinir
```

Isso redefine os dados da conta única e encerra as sessões gerais anteriores. Não
apaga restaurantes nem altera senhas dos administradores dos restaurantes.

## Verificações

Testes em bancos temporários, sem uso do banco original: isolamento entre dois
restaurantes, logins iguais, e-mails obrigatórios, expiração com sessão aberta,
suspensão, renovação, reativação, impedimento de escalada de privilégios, CSRF,
revogação de sessões, datas de calendário, arquivos e notificações por restaurante
e adoção do banco existente sem mudança de seus bytes.

Também foi testado no Chromium o cadastro de restaurantes, login de dois
administradores, links de navegação, envio de pedidos pelo PDV, relatórios,
cardápio público, separação do carrinho e instalação dos workers nos escopos
corretos, em larguras de 320 a 1366 pixels.

Envio real a provedores Web Push e entrega de e-mail não foram testados. A validação
de produção depende de suas configurações de domínio, HTTPS e processo de worker.

Para executar os testes disponíveis:

```bash
python -m unittest discover -s tests -v
```
