> **Atualização mais recente:** leia [ATUALIZACAO_ACESSOS_E_COMANDAS.md](ATUALIZACAO_ACESSOS_E_COMANDAS.md) antes de instalar. Ela modifica o acesso administrativo para e-mail, acrescenta dados pessoais, protege áreas de gestão e inclui comandas e pedidos por QR Code.

> **Nova versão com administrador geral e restaurantes separados.** Antes de iniciar ou atualizar, siga [LEIA_PRIMEIRO_ADMINISTRACAO_GERAL.md](LEIA_PRIMEIRO_ADMINISTRACAO_GERAL.md). Crie sua conta com `python setup_geral.py`. Preserve a pasta `instance`; não use `init_db.py` para atualizar uma instalação existente.

# 🍽️ Restaurante Manager — Pedidos, Cozinha, Entregas e Caixa

Aplicação web desenvolvida com **Python e Flask** para organizar a operação de restaurantes, conectando o atendimento no salão, os pedidos online, a cozinha, os entregadores e a administração.

O sistema possui interfaces específicas para **administrador, garçom, cozinha, entregador e cliente**, com controle de acesso, acompanhamento dos pedidos em tempo real e instalação como **PWA** em celulares e computadores.

## Contexto e objetivo

Desenvolvi este projeto para facilitar a comunicação entre as áreas de um restaurante e centralizar o fluxo de atendimento, desde o registro do pedido até a entrega e a conferência do pagamento.

No salão, o garçom registra os pedidos pelo PDV e identifica a mesa. Pela internet, o cliente acessa o cardápio, monta sua sacola e escolhe entre retirada no caixa ou tele-entrega.

A cozinha recebe os pedidos e atualiza a preparação. O administrador acompanha a operação, gerencia os cadastros, atribui entregadores e controla os recebimentos e o caixa.

## Situação do projeto

🚧 **Em desenvolvimento e validação.**

As funcionalidades descritas estão implementadas na versão apresentada, mas continuam passando por testes e ajustes.

As imagens demonstram as interfaces disponíveis. A utilização em produção depende da configuração da hospedagem e da validação dos fluxos, dispositivos, notificações e rotinas do restaurante.

## Principais funcionalidades

- Autenticação com login e senha.
- Controle de acesso por perfil.
- Gerenciamento da equipe e das contas de clientes.
- Cadastro e edição de produtos e categorias.
- PDV para pedidos do salão.
- Identificação da mesa em destaque.
- Inclusão de quantidades e observações por item.
- Cardápio público com busca, categorias e sacola.
- Cadastro de clientes para pedidos online.
- Pedidos para retirada no caixa ou tele-entrega.
- Seleção da forma de pagamento e informação de troco.
- Acompanhamento dos pedidos por status.
- Fila de preparação da cozinha.
- Notificações em tempo real e alerta sonoro opcional.
- Atribuição de pedidos aos entregadores.
- Confirmação da entrega e registro do pagamento recebido.
- Conferência diária dos valores por entregador.
- Abertura, movimentação e fechamento de caixa.
- Dashboard com indicadores do dia.
- Interface responsiva e instalação como PWA.

## Perfis de acesso

| Perfil | Responsabilidades |
| --- | --- |
| **Administrador** | Gerenciar equipe, clientes, produtos, categorias, configurações da loja, pedidos, entregadores, recebimentos, caixa e dashboard. |
| **Garçom** | Registrar pedidos no PDV, acompanhar os pedidos do salão e confirmar que foram servidos. |
| **Cozinha** | Consultar a fila ativa de pedidos do salão e online e atualizar a preparação. |
| **Entregador** | Consultar somente as tele-entregas atribuídas a ele, confirmar a entrega e informar a forma de pagamento recebida. |
| **Cliente** | Consultar o cardápio, manter sua conta, fazer pedidos online e acompanhar os próprios pedidos. |
| **Visitante** | Consultar o cardápio e montar a sacola, com cadastro e login necessários para confirmar o pedido. |

As permissões são verificadas no backend, inclusive nos acessos diretos às páginas e aos endpoints.

Somente o administrador possui acesso ao gerenciamento do sistema. O cadastro público cria exclusivamente contas de cliente.

## Atendimento no salão

O PDV reúne os produtos por categoria, permite buscar itens e apresenta a montagem do pedido com identificação da mesa, quantidades e observações.

![PDV do garçom](<tela garçom - pdv.png>)

### Fluxo de atendimento

1. O garçom seleciona os produtos no PDV.
2. Informa a mesa, ajusta as quantidades e acrescenta observações.
3. Confere o pedido e envia para a cozinha.
4. A cozinha inicia o preparo.
5. Ao finalizar, marca o pedido como pronto.
6. O garçom responsável recebe um aviso.
7. Após servir o cliente, registra a entrega.
8. O administrador confirma o recebimento com o caixa aberto.

Os garçons visualizam somente os pedidos do salão. Pedidos online e dados dos clientes de tele-entrega não aparecem nesse perfil.

## Cardápio online

O restaurante pode compartilhar o link do cardápio público para receber pedidos de clientes que desejam retirar no caixa ou receber em casa.

O cardápio possui categorias, busca de produtos, preços, descrições e sacola para montagem do pedido.

![Cardápio online do cliente](<tela cliente - cardapio.png>)

### Cadastro do cliente

Para confirmar um pedido, o cliente precisa informar:

- Nome.
- Login.
- Senha.
- CPF.
- Data de nascimento.

Para **retirada no caixa**, não é necessário cadastrar endereço.

Para **tele-entrega**, também são obrigatórios:

- Endereço ou rua.
- Número.
- Bairro.
- Ponto de referência.

O telefone de contato é opcional.

A validação do CPF verifica formato, dígitos verificadores e duplicidade. Não consulta a Receita Federal nem comprova que o documento pertence ao cliente.

### Fluxo do pedido online

1. O cliente acessa o cardápio pelo link.
2. Escolhe os produtos e ajusta quantidades e observações.
3. Faz login ou cria sua conta.
4. Seleciona retirada no caixa ou tele-entrega.
5. Escolhe a forma de pagamento.
6. Confere os produtos, a taxa de entrega e o total.
7. Confirma o pedido.
8. A cozinha e o administrador recebem o pedido.
9. O cliente acompanha o andamento em **Meus pedidos**.

O cliente pode escolher dinheiro, Pix, cartão de crédito ou débito. Para pagamento em dinheiro, pode informar o valor para troco.

**A escolha da forma de pagamento não confirma o recebimento.** O pedido é criado como não pago e depende de conferência posterior.

### Minha conta e meus pedidos

Na própria conta, o cliente pode atualizar nome, endereço e senha. A alteração de senha exige a senha atual.

A área **Meus pedidos** apresenta somente os pedidos daquele cliente, com itens, valores e andamento.

![Acompanhamento dos pedidos pelo cliente](<tela cliente - meus pedidos.png>)

Os pedidos preservam os dados utilizados na compra, incluindo endereço, destinatário, taxa e preferência de pagamento. Alterações posteriores no cadastro não modificam pedidos já registrados.

## Pedidos e status

Os pedidos são apresentados em cartões, com identificação da mesa ou modalidade online, itens, quantidades, observações, valores e situação de pagamento.

A tela possui contadores por status e filtros conforme o acesso do usuário.

![Pedidos na visão do administrador](<tela adm - pedidos.png>)

| Status | Significado |
| --- | --- |
| **Aberto** | Pedido registrado e aguardando preparação. |
| **Em preparo** | Preparação iniciada pela cozinha. |
| **Pronto** | Preparação concluída, aguardando ser servido, retirado ou enviado. |
| **Saiu para entrega** | Pedido de tele-entrega encaminhado ao cliente. |
| **Entregue** | Pedido servido, retirado no caixa ou entregue ao destinatário. |

### Fluxos por modalidade

**Salão e retirada:**

Aberto → Em preparo → Pronto → Entregue.

**Tele-entrega:**

Aberto → Em preparo → Pronto → Saiu para entrega → Entregue.

O andamento do atendimento e a situação do pagamento são informações independentes. Um pedido pode estar entregue e ainda aguardar o registro ou a conferência do recebimento.

## Cozinha

A cozinha possui uma interface dedicada aos pedidos em aberto, em preparo e prontos, reunindo solicitações do salão e online.

O usuário consulta os itens e as observações e pode atualizar o pedido para **Em preparo** e **Pronto**.

![Interface da cozinha](<tela cozinha - pedidos.png>)

Esse perfil não acessa PDV, caixa, equipe ou cadastros administrativos.

Pedidos que já saíram para entrega ou foram concluídos deixam a fila ativa da cozinha.

## Entregadores

O administrador cadastra os usuários com perfil de entregador e atribui as tele-entregas quando os pedidos estão prontos.

Ao enviar o pedido com o entregador, o status passa para **Saiu para entrega**.

![Área do entregador](<tela entregador - minhas entregas.png>)

O entregador visualiza somente os pedidos atribuídos a ele, com:

- Destinatário e endereço.
- Bairro, número e referência.
- Contato, quando informado.
- Itens e total do pedido.
- Preferência de pagamento e informação de troco.

CPF e data de nascimento não são exibidos nessa interface.

Após entregar, o responsável confirma a conclusão e informa a forma de pagamento efetivamente recebida.

Se o administrador já tiver registrado o pagamento, o sistema identifica o pedido como pago antecipadamente e orienta a não cobrar novamente.

As entregas em andamento continuam visíveis mesmo quando iniciadas em dias anteriores. As concluídas podem ser consultadas por dia.

## Acerto dos entregadores

O administrador possui uma área para conferir as entregas concluídas e os valores de cada entregador.

O acompanhamento permite filtrar por data e entregador e consultar:

- Quantidade de entregas concluídas.
- Valor total dos pedidos, incluindo a taxa de entrega.
- Valores recebidos e valores já conferidos.
- Dinheiro pendente de repasse.
- Pix, crédito e débito pendentes de conferência.
- Pedidos pagos antecipadamente.

A confirmação feita pelo entregador registra a entrega e o pagamento informado, mas não movimenta o caixa imediatamente.

O administrador confere o dinheiro e os comprovantes e confirma o acerto. Recebimentos ainda não registrados exigem caixa aberto.

O sistema bloqueia recebimentos duplicados e mantém o histórico da conferência. Pagamentos antecipados não geram uma segunda cobrança.

O saldo representa os valores das vendas a conferir ou repassar ao restaurante. Não corresponde ao cálculo de salário, comissão ou remuneração do entregador.

## Produtos, categorias e equipe

### Produtos

O administrador pode cadastrar e editar produtos com nome, descrição, preço, categoria e identificação visual por emoji, além de ativar ou desativar sua disponibilidade.

Os pedidos preservam o nome e o preço dos itens registrados, mantendo o histórico da venda após alterações no cardápio.

### Categorias

As categorias organizam os produtos e facilitam a navegação no PDV e no cardápio público.

### Equipe

O administrador cadastra usuários, define seus perfis e controla se as contas estão ativas.

Entregadores com pedidos em andamento precisam ter essas entregas reatribuídas antes de serem desativados ou terem o perfil alterado.

### Clientes

A administração pode consultar os cadastros e ativar ou desativar contas de clientes, mantendo a separação entre clientes e equipe.

## Configurações da loja

A área de configurações permite definir:

- Nome do restaurante.
- Aceitação de pedidos online.
- Disponibilidade de tele-entrega.
- Taxa fixa de entrega.

A retirada no caixa não recebe taxa de entrega.

A versão atual não calcula distância nem verifica automaticamente a área atendida. O restaurante precisa conferir a viabilidade do endereço informado.

## Caixa e pagamentos

O módulo de caixa permite:

- Abertura com fundo inicial.
- Registro dos recebimentos.
- Identificação da forma de pagamento.
- Inclusão de suprimentos.
- Registro de sangrias.
- Acompanhamento das movimentações.
- Fechamento com o valor contado.

O saldo esperado em dinheiro considera o fundo inicial, os recebimentos em dinheiro, os suprimentos e as sangrias.

Pix e cartões são registrados separadamente e não são somados ao dinheiro físico.

Os pagamentos são integrais, com uma forma por pedido.

**O sistema registra os pagamentos manualmente. Não realiza cobranças nem possui integração automática com bancos, Pix, maquininhas ou operadoras de cartão.**

## Dashboard

O dashboard oferece ao administrador uma visão do dia com:

- Quantidade de pedidos.
- Valor das vendas.
- Valor recebido.
- Quantidade de pedidos não pagos.
- Lista dos pedidos do dia.

A apuração diária considera o horário de Brasília.

![Dashboard administrativo](<tela adm - dashboard.png>)

## Notificações em tempo real

A aplicação possui uma central de notificações com contador de avisos não lidos e opção de marcar como lidos.

As atualizações utilizam **Server-Sent Events — SSE**, com reconexão automática e consulta periódica de recuperação na lista de pedidos.

![Central de notificações](<notificações.png>)

Os avisos respeitam os perfis e os pedidos envolvidos:

- Cozinha e administração recebem avisos de novos pedidos.
- O garçom responsável é avisado quando seu pedido está pronto.
- Clientes recebem atualizações dos próprios pedidos.
- Entregadores recebem avisos das entregas atribuídas a eles.

### Alerta sonoro

O som é opcional e pode ser ativado e testado pelo menu.

O navegador exige interação para liberar a reprodução e pode solicitar uma nova autorização após reabrir o sistema.

Volume, modo silencioso e restrições do dispositivo podem interferir no alerta.

### Notificações com o aplicativo fechado

O projeto inclui suporte a **Web Push**, que depende de:

- Configuração das chaves no servidor.
- Processo de envio em execução.
- Acesso por HTTPS.
- Navegador compatível.
- Permissão concedida pelo usuário.

A configuração é realizada com `setup_push.py`. O arquivo `run.py` inicia o servidor e o processo de envio.

Se a hospedagem iniciar somente a aplicação WSGI, o `push_worker.py` deve ser executado como processo separado.

O som das notificações em segundo plano é controlado pelo sistema operacional. A entrega também depende de internet, permissões e restrições de bateria.

## Responsividade e PWA

A interface foi adaptada para uso em celulares, tablets e computadores, com:

- Menu superior fixo.
- Navegação conforme o perfil.
- Atalhos adaptados ao celular.
- Botões para interação por toque.
- Sacola ajustada ao espaço disponível.
- Identificação da mesa em destaque.
- Cores e textos para diferenciar os status.

A aplicação pode ser instalada como **Progressive Web App — PWA**, utilizando manifesto, ícones e service worker.

Em navegadores compatíveis, a opção **Instalar app** permite adicionar o sistema ao dispositivo.

No iPhone e iPad compatíveis, a instalação é feita por **Compartilhar → Adicionar à Tela de Início**.

A instalação e o Web Push exigem HTTPS, com exceção de `localhost` para desenvolvimento no próprio computador.

Sem conexão, o aplicativo apresenta uma tela de reconexão. Pedidos, pagamentos e alterações exigem internet e não entram em uma fila offline.

## Tecnologias utilizadas

| Camada | Tecnologias |
| --- | --- |
| Backend | Python e Flask |
| Persistência | SQLAlchemy e Flask-SQLAlchemy |
| Banco de dados | SQLite |
| Autenticação | Sessões do Flask e hash de senhas com Werkzeug |
| Interface | HTML, CSS e JavaScript |
| Templates | Jinja2 |
| Comunicação | Endpoints HTTP com JSON e SSE |
| Notificações | Web Push, pywebpush e chaves VAPID |
| Proteção de dados | Cryptography/Fernet |
| Aplicação instalável | Manifesto PWA e service worker |
| Servidor | Waitress |
| Formatação | Black e Prettier |

## Organização do código

```text
restaurante_manager/
├── app.py
├── config.py
├── models.py
├── orders_service.py
├── customers.py
├── customer_security.py
├── couriers.py
├── notifications.py
├── push_worker.py
├── setup_push.py
├── init_db.py
├── migrate.py
├── run.py
├── requirements.txt
├── requirements-dev.txt
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   ├── icons/
│   ├── manifest.webmanifest
│   ├── sw.js
│   └── offline.html
├── tests/
└── instance/
```

| Arquivo ou diretório | Responsabilidade |
| --- | --- |
| `app.py` | Configuração da aplicação, autenticação e operações internas. |
| `config.py` | Configurações e caminhos dos dados persistentes. |
| `models.py` | Modelos e relacionamentos do banco. |
| `orders_service.py` | Tratamento dos itens e serialização dos pedidos. |
| `customers.py` | Cadastro, conta, cardápio e pedidos online. |
| `customer_security.py` | Validações e proteção dos dados de clientes. |
| `couriers.py` | Atribuição, conclusão e acerto das entregas. |
| `notifications.py` | Central de avisos, SSE e inscrições push. |
| `push_worker.py` | Processamento da fila de notificações push. |
| `setup_push.py` | Configuração das chaves de notificação. |
| `init_db.py` | Inicialização de uma instalação nova. |
| `migrate.py` | Atualização aditiva do banco. |
| `run.py` | Inicialização do servidor e do worker. |
| `templates/` | Páginas da interface. |
| `static/` | Estilos, scripts, ícones e recursos PWA. |
| `tests/` | Testes automatizados. |
| `instance/` | Banco de dados e chaves locais; não deve ser versionada. |

## Como executar

Para uma instalação nova no Windows, abra o PowerShell na pasta que contém `app.py`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe init_db.py
.\.venv\Scripts\python.exe run.py
```

A inicialização solicita os dados do administrador. Não existe senha padrão.

Acesse:

- Sistema: `http://127.0.0.1:5000`
- Cardápio público: `http://127.0.0.1:5000/cardapio`

Para configurar o Web Push:

```powershell
.\.venv\Scripts\python.exe setup_push.py
```

Informe o e-mail de contato, reinicie com `run.py` e ative os avisos em cada dispositivo.

Em instalações existentes, preserve a pasta `instance/` e siga as instruções de atualização antes de executar scripts de inicialização.

## Aspectos técnicos

- Modelagem de usuários, produtos, categorias, pedidos, itens, clientes, entregas e caixa.
- Separação das interfaces e operações por perfil.
- Controle de acesso no backend.
- Proteção CSRF nas operações de alteração.
- Senhas armazenadas com hash.
- CPF cifrado e exibido de forma mascarada.
- Limitação de tentativas de login e cadastro.
- Valores monetários armazenados em centavos.
- Totais calculados no servidor.
- Preservação dos dados do pedido no momento da compra.
- Controle de repetição no checkout online.
- Bloqueio de recebimentos duplicados.
- Conferência de entregas em transação.
- Persistência das notificações e da fila Web Push.

A pasta `instance/` contém o banco e as chaves utilizadas pelo sistema. Ela deve ser preservada nas atualizações, incluída nos backups e mantida fora do repositório público.

## Testes

A suíte automatizada pode ser executada com:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes abrangem permissões, pedidos, clientes, caixa, notificações, entregadores e migração.

A validação real de Web Push, instalação PWA e som deve ser realizada nos dispositivos e no domínio da implantação.

## Limitações atuais

- Pagamentos registrados manualmente.
- Sem integração bancária ou emissão fiscal.
- Sem pagamento dividido.
- Sem controle de estoque.
- Sem cálculo de entrega por distância.
- Sem roteirização ou rastreamento por GPS.
- Sem cálculo de comissão de entregadores.
- Sem recuperação de senha por e-mail.
- Sem envio de pedidos e recebimentos offline.
- Lista operacional limitada aos 200 pedidos mais recentes.
- Capacidade de uso simultâneo ainda precisa ser validada para operação comercial.

## Próximas etapas

- Validar o ciclo completo com usuários de cada perfil.
- Testar PWA, notificações e áudio em diferentes dispositivos.
- Ampliar os testes de conexão e uso simultâneo.
- Validar o fechamento de caixa e os acertos diários na operação.
- Melhorar acessibilidade, mensagens de erro e experiência de uso.
- Evoluir relatórios e recuperação de acesso conforme as necessidades do projeto.

## Autor

Desenvolvido por **Lovan Goulart**, com apoio de ferramentas de inteligência artificial durante o desenvolvimento.

[GitHub](https://github.com/LovanGoulart)
