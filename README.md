# 🍽️ Restaurante Manager

**Comanda eletrônica, cardápio digital e gestão da operação de restaurantes — com evolução para SaaS.**

Aplicação web desenvolvida com **Python, Flask e SQLAlchemy** para conectar atendimento, cozinha, entregadores, clientes e administração em um único fluxo. O projeto reúne pedidos no salão, autoatendimento por QR Code, retirada, delivery, controle de caixa, relatórios e um programa de fidelidade por pontos.

A plataforma também possui uma camada de **administração geral**, com cadastro de restaurantes, ambientes de dados separados, controle de administradores e liberação de acesso por períodos de validade.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![PWA](https://img.shields.io/badge/PWA-Instal%C3%A1vel-5A0FC8?style=flat-square)

## Índice

- [Contexto e objetivo](#contexto-e-objetivo)
- [Situação do projeto](#situação-do-projeto)
- [Visão geral das funcionalidades](#visão-geral-das-funcionalidades)
- [Perfis de acesso](#perfis-de-acesso)
- [Administração geral e SaaS](#administração-geral-e-estrutura-para-saas)
- [Pedidos, PDV e comandas](#pedidos-pdv-e-comandas)
- [Atendimento por QR Code](#atendimento-no-salão-por-qr-code)
- [Cardápio e pedidos de casa](#cardápio-digital-e-pedidos-de-casa)
- [Cozinha e salão](#cozinha-e-entrega-dos-itens-no-salão)
- [Tele-entrega e acertos](#tele-entrega-e-acerto-dos-entregadores)
- [Caixa](#caixa-e-recebimentos)
- [Fidelidade](#programa-de-fidelidade-por-pontos)
- [Produtos e pizzas](#produtos-categorias-e-composição-dos-pedidos)
- [Equipe, clientes e gestão](#equipe-clientes-e-proteção-da-gestão)
- [Dashboard e relatórios](#dashboard-e-relatórios-de-vendas)
- [Personalização](#personalização-do-estabelecimento)
- [Notificações](#notificações-e-atualizações-em-tempo-real)
- [PWA, idiomas e aparência](#pwa-idiomas-e-aparência)
- [Integração fiscal](#integração-fiscal)
- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura-e-organização-do-código)
- [Segurança e dados](#segurança-e-preservação-dos-dados)
- [Execução local](#execução-local)
- [Testes](#testes-e-validação)
- [Evolução para SaaS](#evolução-para-saas)
- [Competências demonstradas](#o-que-este-projeto-demonstra)
- [Autor](#autor)

## Contexto e objetivo

O Restaurante Manager foi desenvolvido para organizar etapas que precisam se comunicar durante o atendimento: registrar o pedido, identificar a mesa ou o endereço, encaminhar os itens para a cozinha, acompanhar o preparo, realizar a entrega e conferir o recebimento.

O sistema atende diferentes formas de consumo sem exigir que todos os usuários utilizem a mesma interface. O garçom trabalha com mesas e comandas; a cozinha acompanha a produção; o entregador consulta suas entregas; o cliente realiza e acompanha pedidos; o administrador supervisiona a operação.

Além da gestão de um estabelecimento, o projeto está sendo estruturado para atender **vários restaurantes sob uma mesma plataforma**, com separação de dados e controle central de acesso.

## Situação do projeto

**Em desenvolvimento e evolução para comercialização como SaaS.**

A versão documentada já contempla os módulos operacionais, a administração de múltiplos restaurantes e o controle manual de planos. A oferta comercial ainda exige validações de implantação, capacidade, backups, recuperação e operação em produção.

O controle de validade dos planos está implementado. **A cobrança recorrente automática da plataforma é uma evolução planejada.**

## Visão geral das funcionalidades

| Área | Recursos |
| --- | --- |
| Administração geral | Restaurantes separados, administradores, períodos de acesso, renovação, suspensão e histórico de alterações. |
| Atendimento | PDV, mesa, comanda, busca por comanda e acompanhamento dos pedidos. |
| Salão por QR Code | Entrada sem conta convencional, identificação por nome e mesa e vinculação da comanda pelo garçom. |
| Pedidos online | Cardápio público, cadastro de clientes, sacola, retirada e tele-entrega. |
| Cozinha | Fila de pedidos, preparo, conclusão e acompanhamento dos itens. |
| Entregas | Atribuição de entregador, registro da entrega, forma de pagamento e acerto financeiro. |
| Caixa | Abertura, recebimentos, sangria, suprimento, fechamento e histórico. |
| Fidelidade | Regras de pontuação, recompensas, resgate, saldo e histórico de movimentações. |
| Gestão | Produtos, categorias, equipe, clientes e proteção de áreas administrativas. |
| Relatórios | Indicadores, períodos, gráficos, rankings e exportação para Excel. |
| Personalização | Nome, cores, capa do cardápio e fotos dos produtos. |
| Notificações | Central de avisos, atualizações por SSE, som, vibração e Web Push configurável. |
| Experiência de uso | Interface responsiva, PWA, português, inglês, espanhol e temas claro/escuro. |
| Integração fiscal | Módulo de NFC-e via Focus NFe, com configuração e processamento próprios, sujeito à homologação. |

## Perfis de acesso

As permissões são verificadas no servidor, além da organização visual dos menus.

| Perfil | Responsabilidades |
| --- | --- |
| Administrador geral | Gerenciar a plataforma, cadastrar restaurantes e administradores e controlar a validade dos acessos. |
| Administrador do restaurante | Supervisionar pedidos, operar o PDV e o caixa, gerenciar entregas, cadastros, fidelidade, relatórios e configurações do estabelecimento. |
| Garçom | Atender o salão, registrar pedidos, vincular mesas e comandas e acompanhar a entrega dos itens. |
| Cozinha | Consultar pedidos em produção e atualizar preparo e conclusão. |
| Entregador | Consultar as entregas atribuídas, registrar sua conclusão e informar o recebimento. |
| Cliente cadastrado | Pedir para retirada ou delivery, acompanhar seus pedidos e participar da fidelidade quando habilitada. |
| Cliente do salão por QR Code | Informar nome e mesa, pedir pelo celular e acompanhar o atendimento na sessão do navegador. |

## Administração geral e estrutura para SaaS

### Cadastro de restaurantes e planos

O administrador geral possui uma área própria, separada da operação dos restaurantes, com:

- Cadastro do estabelecimento e de seu identificador de acesso.
- Endereço individual no formato `/r/identificador/`.
- Cadastro dos dados do administrador responsável.
- Liberação de acesso por **1, 3, 6 ou 12 meses**.
- Consulta de validade e situação do restaurante.
- Renovação e ativação de planos.
- Suspensão e reativação de acesso.
- Histórico das alterações administrativas.
- Navegação em abas para acessos e planos, cadastro e histórico.

Quando um plano ainda está vigente, a renovação soma o período à validade existente. Quando está vencido, o novo período é contado a partir da renovação. O acesso depende da situação do restaurante, da validade do plano e da situação do usuário.

### Administradores de cada estabelecimento

É possível cadastrar mais de um administrador para o mesmo restaurante, editar dados pessoais, atualizar o e-mail de acesso, ativar ou desativar a conta e redefinir a senha.

Os dados do administrador e o bloco de **senhas e acesso** aparecem associados ao mesmo usuário, lado a lado no desktop e reorganizados no celular. O menu superior permanece visível durante a rolagem.

### Separação dos ambientes

Cada restaurante utiliza seu próprio banco SQLite e diretório de dados. A plataforma mantém um registro central para localizar o ambiente correspondente ao identificador da URL e aplicar as regras de acesso.

Essa organização constitui a base multi-restaurante do projeto. A arquitetura atual utiliza isolamento por banco e arquivos, e sua capacidade precisa ser avaliada conforme o volume de estabelecimentos e de operações simultâneas.

![Administração geral com acessos e planos de restaurantes](img/tela%20inicial%20-%20clientes%20adm%20-%20administrador%20geral.png)

## Pedidos, PDV e comandas

### Registro e acompanhamento

- PDV para o atendimento interno.
- Cardápio organizado por categorias.
- Busca de produtos e seleção de quantidades.
- Observações e opções de composição dos produtos.
- Identificação de mesa e comanda.
- Encaminhamento dos pedidos para a cozinha.
- Acompanhamento da situação do pedido e de seus itens.
- Identificação de pagamento pendente ou realizado.
- Consulta dos detalhes em um card/modal.

Os totais são calculados no servidor. O pedido preserva informações dos itens no momento da compra, permitindo consultar o registro mesmo após alterações no catálogo.

### Painel operacional

Os cards apresentam informações como número do pedido, mesa/comanda, cliente, resumo dos itens, valor, pagamento e andamento do atendimento.

A faixa de indicadores permite acompanhar:

1. A receber.
2. Pronto.
3. Em preparo.
4. Enviado à cozinha.
5. Saiu para entrega.
6. Aguardando comanda.

A tela dispõe de busca por comanda, inclusive por leitura com dispositivo que simule digitação, filtros de situação e filtro de origem: **salão, retirada, tele-entrega e fidelidade**.

As cores ajudam a distinguir os estágios: verde para pronto, azul para preparo, amarelo para envio à cozinha, vermelho para valores a receber e lilás para pedidos aguardando comanda. As apresentações são adaptadas ao contexto e ao perfil; os detalhes do pedido mantêm sua própria organização visual.

Pedidos resgatados com pontos seguem a organização operacional correspondente ao seu status. O fato de o produto já estar pago por pontos não substitui o acompanhamento de preparo e entrega.

### Histórico de finalizados

No painel administrativo, os pedidos finalizados exibidos na lista operacional são os do dia atual. Os demais continuam acessíveis em uma página específica de histórico.

- Data atual selecionada inicialmente.
- Alteração automática da consulta ao trocar a data.
- Opção de visualizar todos os finalizados.
- Paginação dos registros.
- Abertura e fechamento dos detalhes mantendo o usuário na página de histórico.
- Referência de datas no horário de Brasília.

O estado financeiro é tratado separadamente do atendimento: um pedido pago ainda pode estar em preparo ou aguardando entrega.

![Pedidos administrativos com indicadores, filtros e cards por status](img/Tela%20inicial%20-%20administrador.png)

## Atendimento no salão por QR Code

### Entrada pelo celular

O cliente escaneia o QR Code do estabelecimento e informa **nome e número da mesa**, sem precisar criar uma conta convencional ou digitar senha.

Após a identificação, nome e mesa aparecem na interface. O cliente acessa o cardápio, monta o pedido e acompanha seu atendimento no navegador utilizado.

### Vinculação da comanda

1. O cliente informa nome e mesa e envia o pedido.
2. O pedido é identificado como aguardando comanda.
3. Na lista do garçom, pedidos nessa condição recebem prioridade.
4. O garçom confere a mesa e define a comanda.
5. O pedido volta à organização normal da fila.
6. Novos pedidos daquela sessão utilizam o vínculo de mesa e comanda.
7. Ao pagar a conta vinculada, o acesso do visitante é encerrado automaticamente.

O acesso do salão está associado à sessão do navegador. A experiência é diferente da conta persistente do cliente que pede de casa.

### Plaquinha pronta para impressão

O administrador pode gerar e baixar um PDF com:

- Nome do restaurante em destaque.
- Chamada para pedir pelo celular.
- QR Code do cardápio do salão.
- Arte vertical de **10 × 15 cm**, adequada para suporte de mesa.
- Código com dimensão útil superior ao mínimo de **5 × 5 cm** na composição prevista.
- Posicionamento em folha A4 para impressão em tamanho real e recorte.

O QR Code utiliza o endereço de acesso ao sistema. Para os clientes utilizarem seus próprios celulares, deve apontar para uma URL pública válida; `127.0.0.1` só identifica o próprio dispositivo.

<img src="img/tela%20de%20acesso%20do%20cliente%20que%20esta%20no%20sal%C3%A3o%20e%20utiliza%20qrcode%20para%20acessar%20o%20cardapio%20-%20mobile.png" alt="Entrada do cliente do salão por QR Code com nome e mesa" width="340">

## Cardápio digital e pedidos de casa

O cliente pode consultar o cardápio público antes de entrar. Para enviar pedidos de retirada ou delivery, utiliza sua própria conta.

- Cadastro e autenticação de clientes.
- Validação de CPF e dados cadastrais.
- Identificação e atualização do perfil.
- Categorias e fotos dos produtos.
- Escolha de opções, adicionais e observações.
- Sacola com quantidades e total.
- Barra de acesso à sacola exibida após a inclusão de itens.
- Escolha entre **retirada no estabelecimento** e **tele-entrega**.
- Endereço de entrega com os campos necessários ao atendimento.
- Taxa de entrega configurável pelo restaurante.
- Seleção de forma de pagamento.
- Consulta dos próprios pedidos e de suas atualizações.

O restaurante pode habilitar ou interromper o recebimento de pedidos online e controlar a disponibilidade da tele-entrega.

No celular, a navegação utiliza menu inferior e a opção **Ver mais**. No desktop, as ações são organizadas no menu superior. A apresentação muda conforme o estado de autenticação e o contexto de acesso.

<img src="img/tela%20inicial%20mobile%20responsivo%20-%20cliente%20de%20casa.png" alt="Cardápio mobile do cliente com categorias, produtos e sacola" width="340">

## Cozinha e entrega dos itens no salão

O perfil de cozinha concentra a interface nos pedidos relevantes à produção.

- Recebimento de novos pedidos.
- Consulta de produtos, quantidades e observações.
- Identificação de mesa/comanda ou modalidade do pedido.
- Marcação do início do preparo.
- Marcação de pedido pronto.
- Acompanhamento das etapas dos itens por checklist.

O garçom acompanha os pedidos do salão, identifica itens prontos e registra sua entrega à mesa. A separação entre preparo e entrega permite que o andamento da cozinha não seja confundido com a conclusão do atendimento.

## Tele-entrega e acerto dos entregadores

### Operação de entrega

- Consulta dos pedidos de tele-entrega.
- Atribuição do pedido a um entregador pelo administrador.
- Visualização das entregas atribuídas ao usuário responsável.
- Identificação do cliente e endereço.
- Registro de conclusão da entrega.
- Informação da forma de pagamento e do valor recebido.
- Consulta por data.

### Conferência financeira

A área de acerto permite conferir as entregas e os valores de cada entregador, distinguindo o dinheiro a repassar dos pagamentos eletrônicos a conferir.

O administrador seleciona as entregas, confirma a conferência e registra os recebimentos ainda pendentes no caixa aberto. A operação possui verificações para evitar duplicidade de recebimento e de acerto.

Pagamentos informados por dinheiro, Pix, crédito ou débito são **registros operacionais**. O registro de Pix ou cartão não representa, por si só, uma confirmação automática de banco ou adquirente.

## Caixa e recebimentos

- Abertura do caixa com valor inicial.
- Registro dos recebimentos de pedidos.
- Separação por forma de pagamento.
- Registro de suprimentos.
- Registro de sangrias.
- Validação de saldo em dinheiro para sangria.
- Consulta dos movimentos do caixa aberto.
- Cálculo do saldo em dinheiro.
- Fechamento com valor contado.
- Histórico de caixas.
- Integração com os acertos dos entregadores.

Operações que dependem do caixa aberto são validadas no servidor. O sistema também verifica se o pedido já teve seu recebimento registrado.

## Programa de fidelidade por pontos

### Participação e configuração

A fidelidade atende exclusivamente a **pedidos feitos pelo próprio cliente cadastrado**, nas modalidades retirada e tele-entrega. Pedidos presenciais registrados pelo atendimento e sessões de salão por QR Code não participam desse acúmulo.

O administrador pode:

- Habilitar ou desabilitar o programa.
- Definir um valor de referência e a quantidade de pontos correspondente.
- Cadastrar produtos do catálogo como recompensas.
- Definir o custo em pontos de cada recompensa.
- Editar e retirar recompensas de disponibilidade.
- Consultar saldo e histórico por cliente.
- Acompanhar resgates recentes e seus detalhes.
- Cancelar resgates elegíveis antes do preparo, com devolução dos pontos.

### Cálculo e crédito

Os pontos são calculados em **blocos completos por pedido**, sobre o valor dos produtos, sem incluir taxa de entrega.

Exemplo de regra: **a cada R$ 20,00 em produtos, o cliente recebe 3 pontos**.

| Valor em produtos | Pontos previstos |
| --- | --- |
| R$ 20,00 | 3 |
| R$ 39,90 | 3 |
| R$ 40,00 | 6 |
| R$ 60,00 | 9 |

O crédito ocorre quando o pedido está **pago e entregue/retirado**. A configuração aplicável é registrada na compra, de modo que alterações posteriores não recalculam os pontos daquele pedido. Não há atribuição retroativa aos pedidos anteriores à implementação.

### Resgate de recompensas

O cliente consulta saldo, custo dos produtos e disponibilidade para resgate. A confirmação é feita em um pedido próprio de recompensa, separado de uma compra comum.

- **Retirada:** o produto resgatado não gera cobrança em dinheiro.
- **Delivery:** permanece apenas a taxa de entrega, quando configurada.
- Os pontos são descontados na transação que confirma o pedido válido.
- O servidor verifica saldo, disponibilidade e eventual mudança do custo em pontos.
- Resgates sem valor monetário são identificados como pagos, sem criar recebimento fictício no caixa.
- Resgates não geram um novo ciclo de acúmulo de pontos.

### Histórico e consistência

O saldo é obtido das movimentações de ganho, resgate e estorno. Os registros incluem cliente, data, quantidade de pontos e pedido relacionado.

As regras incluem proteção contra crédito duplicado, isolamento dos saldos por cliente e devolução única dos pontos em cancelamentos permitidos. O cancelamento é limitado a resgates ainda aguardando preparo e sem condições financeiras que impeçam o estorno previsto.

Ao desabilitar o programa, o acesso do cliente à funcionalidade é bloqueado e o menu fica oculto, mas os saldos são preservados para uma futura reativação.

A administração é organizada em abas: **Programa e pontuação, Cadastrar recompensa, Produtos disponíveis, Saldo e histórico e Resgates recentes**.

![Configuração do programa de fidelidade e regra de pontos](img/programa%20fidelidade%20-%20administrador.png)

## Produtos, categorias e composição dos pedidos

### Catálogo

- Cadastro e edição de categorias.
- Cadastro de produtos com nome, descrição, preço e categoria.
- Ativação e desativação de produtos.
- Exclusão lógica para preservar referências históricas.
- Foto real ou ícone para apresentação do produto.
- Grupos de opções configuráveis por produto.
- Escolhas simples, múltiplas e campos de texto.
- Opções obrigatórias ou opcionais, limites de seleção e valores adicionais.
- Campo de observações configurável.

### Configuração de pizzas

O projeto possui um fluxo próprio para pizzas, com os sabores vinculados aos produtos da categoria correspondente.

- Tamanhos broto, média, grande e família.
- Quantidade de fatias por tamanho.
- Limite de sabores por tamanho.
- Disponibilidade de cada tamanho.
- Preço fixo ou composição baseada na média dos sabores.
- Massas, bordas e acompanhamentos configuráveis.
- Fotos e descrição dos sabores.
- Validação das escolhas e recálculo do preço no servidor.

As opções enviadas pelo navegador são conferidas com a configuração vigente antes da confirmação do pedido.

![Gestão de produtos com fotos, edição e opções de composição](img/controle%20dos%20produtos%20-%20administrador.png)

## Equipe, clientes e proteção da gestão

### Equipe

O administrador cadastra os usuários da operação, define perfil, login e senha e controla se a conta está ativa. Os menus e as operações disponíveis acompanham essas permissões.

![Cadastro e gerenciamento da equipe do restaurante](img/controle%20da%20equipe%20-%20administrador.png)

### Clientes

- Consulta dos clientes cadastrados.
- Controle de ativação das contas.
- Exportação da base em Excel.
- Informações de relacionamento baseadas no histórico de pedidos.
- Análise de frequência e preferências de consumo na exportação.
- Sugestões derivadas dos produtos mais pedidos por cliente.

A exportação apoia a análise comercial; não realiza disparos automáticos de campanhas.

### Bloqueio das áreas administrativas

O administrador pode habilitar a confirmação adicional de senha para áreas de gestão, incluindo produtos, categorias, equipe, clientes, relatórios, configurações e fidelidade.

A proteção também é aplicada aos endpoints correspondentes, evitando depender apenas de esconder botões na interface.

![Painel de controle com áreas administrativas protegidas](img/painel%20de%20controle%20-%20administrador.png)

## Dashboard e relatórios de vendas

O dashboard apresenta uma visão do dia, com pedidos, vendas, valores recebidos e pedidos não pagos.

A área de relatórios permite explorar o movimento do restaurante por diferentes perspectivas:

- Períodos de dia, semana, mês e ano.
- Seleção de data de referência.
- Filtro de pedidos considerados, incluindo somente pagos.
- Quantidade de pedidos e unidades.
- Valor total dos pedidos.
- Valores marcados como pagos e não pagos.
- Ticket médio.
- Evolução de vendas por hora ou por dia, conforme o período.
- Separação dos valores de produtos e entrega.
- Análise por categoria.
- Ranking dos melhores clientes.
- Produtos mais vendidos.
- Consulta dos pedidos que compõem o relatório.
- Exportação por seção ou consolidada em **`.xlsx`**.

A interface utiliza abas para **Visão geral, Categorias, Melhores clientes, Mais vendidos e Pedidos**, evitando concentrar todas as análises em uma página extensa.

Datas são apresentadas no padrão brasileiro, com referência ao fuso **America/Sao_Paulo**, e os valores monetários são exibidos em reais.

![Relatórios de vendas com períodos, indicadores, abas e exportação Excel](img/relat%C3%B3rios%20-%20administrador.png)

## Personalização do estabelecimento

Cada restaurante pode configurar sua apresentação no sistema:

- Nome do estabelecimento.
- Cores do menu, botões e elementos principais.
- Capa do cardápio público.
- Título e descrição da capa.
- Fotos individuais dos produtos.
- Uso de ícones quando não houver foto.
- Busca de produtos na área de gerenciamento de imagens.

As imagens podem ser enviadas em **JPG, PNG ou WebP**, dentro dos limites validados pela aplicação. A personalização é armazenada no ambiente do restaurante.

![Personalização das cores, capa e fotos dos produtos](img/personaliza%C3%A7%C3%A3o%20-%20administrador.png)

## Notificações e atualizações em tempo real

### Canais de comunicação

- Atualização das interfaces conectadas por **Server-Sent Events — SSE**.
- Central de notificações vinculada ao usuário.
- Indicador de notificações não lidas.
- Marcação individual ao abrir um aviso e opção de marcar como lidas.
- Diferenciação visual dos avisos já lidos.
- Direcionamento ao pedido relacionado.
- Alertas visuais na aplicação.
- Som configurável e botão para testar o alerta.
- Preferência de som persistida no navegador.
- Solicitação de vibração nos dispositivos compatíveis.
- Web Push com inscrições por dispositivo e fila persistente de envio.

### Avisos conforme o atendimento

Os eventos são direcionados conforme o perfil e a relação do usuário com o pedido.

| Contexto do cliente | Comportamento |
| --- | --- |
| Delivery | Recebe aviso de preparo; a conclusão na cozinha não gera o aviso de pronto para o cliente. O aviso de trânsito é liberado após cinco minutos da atribuição da entrega, se o pedido continuar elegível. |
| Retirada | Continua recebendo atualizações de preparo e de pedido pronto para retirada. |
| Salão por QR Code | Não recebe aviso de que o pedido ficou pronto na cozinha; o atendimento acompanha essa etapa para levar os itens à mesa. |
| Equipe | Recebe os eventos pertinentes ao seu perfil e às suas responsabilidades. |

O status apresentado ao cliente de delivery acompanha a regra do aviso, evitando mostrar a saída imediatamente após a atribuição do entregador.

### Condições de funcionamento

Som e vibração dependem das permissões, do navegador e das políticas do dispositivo. O sistema solicita a apresentação de notificações pelo sistema operacional, mas **o formato heads-up/flutuante e o comportamento no modo silencioso dependem do aparelho**.

Web Push exige configuração de chaves VAPID, permissão do usuário, HTTPS na hospedagem e um processador ativo. A preferência de som pode ser preservada, mas o navegador ainda pode exigir interação para liberar áudio em uma nova sessão.

## PWA, idiomas e aparência

O Restaurante Manager pode ser instalado como **Progressive Web App**, utilizando manifesto, ícones e service worker.

- Instalação em navegadores e dispositivos compatíveis.
- Acesso em janela própria.
- Orientações de instalação conforme o ambiente.
- Indicação de aplicativo instalado quando detectado pelo fluxo disponível.
- Recursos estáticos em cache e página de indisponibilidade offline.
- Escopo de recursos PWA associado ao restaurante.
- Experiência própria de instalação para a administração geral.

O cache não transforma a aplicação em um sistema de pedidos offline: envio de pedidos, confirmação de pagamentos e demais alterações dependem de comunicação com o servidor.

A interface possui opções de **português brasileiro, inglês e espanhol**, além de **modo claro e modo escuro**. A seleção é aplicada sem uma etapa adicional de confirmação. As preferências são preservadas no navegador; textos cadastrados pelo restaurante, como nomes e descrições de produtos, não são traduzidos automaticamente.

## Integração fiscal

A versão evoluída do projeto inclui um módulo de **NFC-e por meio da API Focus NFe**, separado das operações comuns de pagamento.

- Configuração do ambiente fiscal.
- Credenciais e dados necessários à integração.
- Teste de comunicação com o provedor.
- Configuração e envio de certificado pelo fluxo disponível.
- Cadastro de regras fiscais.
- Preparação de emissão para pedidos pagos.
- Consulta de documentos e acompanhamento do processamento.
- Tratamento de dados do destinatário e de documentos ainda não enviados.
- Processador fiscal próprio para as bases dos restaurantes.
- Separação entre homologação e produção.

**A presença do módulo não significa emissão fiscal homologada para qualquer estabelecimento.** O uso exige conta no provedor, configuração tributária adequada, certificado e demais requisitos aplicáveis, além de validação com a contabilidade e testes de homologação. A produção possui habilitação específica por configuração.

## Tecnologias

| Camada | Tecnologias e recursos utilizados |
| --- | --- |
| Backend | Python, Flask e Blueprints. |
| Persistência | SQLAlchemy, Flask-SQLAlchemy e SQLite na arquitetura atual. |
| Autenticação | Sessões do Flask, verificações de perfil e hash de senhas com Werkzeug. |
| Interface | HTML, Jinja2, CSS e JavaScript. |
| Atualizações | SSE, EventSource e chamadas HTTP da interface. |
| Notificações externas | Web Push, pywebpush, service worker e chaves VAPID. |
| Proteção de dados | cryptography/Fernet para campos e credenciais protegidos. |
| Planilhas | openpyxl. |
| Imagens | Pillow. |
| QR Code e PDF | qrcode e ReportLab. |
| Datas | datetime, zoneinfo e tzdata. |
| Execução local | Waitress e processo de trabalho para notificações. |
| Qualidade | unittest, Black e Prettier. |
| Versionamento | Git e GitHub. |

## Arquitetura e organização do código

O projeto utiliza uma fábrica de aplicação para os ambientes dos restaurantes. Módulos específicos concentram os fluxos de negócio, enquanto templates e arquivos estáticos compõem a interface.

O `RestaurantDispatcher`, na camada de plataforma, identifica o restaurante pelo caminho da requisição e encaminha o acesso à aplicação correspondente.

| Arquivo ou diretório | Responsabilidade |
| --- | --- |
| `app.py` | Fábrica da aplicação, autenticação interna, pedidos, PDV, caixa e registro dos módulos. |
| `platform_admin.py` | Administração geral, registro dos restaurantes, planos, administradores e despacho entre ambientes. |
| `setup_geral.py` | Configuração da conta do proprietário da plataforma pelo terminal. |
| `models.py` | Modelos operacionais: usuários, produtos, pedidos, itens, caixa, clientes, entregas e notificações. |
| `orders_service.py` | Itens, serialização e regras de apresentação/andamento dos pedidos. |
| `customers.py` | Conta do cliente, cardápio e checkout online. |
| `customer_security.py` | Validações de cadastro e controles de acesso dos clientes. |
| `salon_qr.py` | Sessões de salão, pedidos por QR Code e vinculação de comanda. |
| `qr_poster.py` | Geração do cartaz de mesa em PDF. |
| `couriers.py` | Atribuição, conclusão e acerto de entregas. |
| `loyalty.py` e `loyalty_models.py` | Configuração, cálculo, movimentações e resgates da fidelidade. |
| `order_history.py` | Consulta dos pedidos finalizados por data. |
| `product_options.py` e `pizza_menu.py` | Opções dos produtos e composição de pizzas. |
| `sales_reports.py` e `leads_export.py` | Relatórios de vendas e exportações analíticas de clientes. |
| `management_access.py` | Proteção adicional das áreas de gestão. |
| `appearance.py` e `ui_preferences.py` | Identidade visual, fotos, idiomas e temas. |
| `notifications.py` e `push_worker.py` | Eventos persistentes, SSE, avisos agendados e processamento Web Push. |
| `fiscal*.py` | Interface, modelos, integração com provedor e processamento fiscal. |
| `migrate.py` e `migrate_loyalty.py` | Rotinas de evolução do banco e instalação das tabelas de fidelidade. |
| `templates/` | Páginas renderizadas pelo Flask/Jinja2. |
| `static/` | CSS, JavaScript, ícones, traduções e recursos PWA. |
| `tests/` | Testes automatizados. |
| `img/` | Capturas de tela utilizadas nesta documentação. |
| `instance/` | Dados persistentes, bases e chaves locais; deve permanecer fora do versionamento público. |

### Decisões de implementação

- **Valores monetários em centavos:** reduz problemas de arredondamento com ponto flutuante.
- **Totais calculados no backend:** valores enviados pela interface não são aceitos como autoridade final.
- **Snapshots dos pedidos:** mantêm o registro da compra e da regra de fidelidade aplicável.
- **Transações nas operações críticas:** coordenam confirmações de pedidos, recebimentos, acertos e pontos.
- **Restrições de unicidade e idempotência:** ajudam a impedir repetição de créditos e recebimentos.
- **Eventos persistidos com a operação:** notificações e fila de envio ficam relacionadas à alteração de negócio.
- **Separação de preparo, entrega e pagamento:** permite representar pedidos pagos ainda em produção e entregues ainda a receber.
- **Banco e arquivos por restaurante:** organizam o isolamento da versão multi-restaurante.

## Segurança e preservação dos dados

O projeto inclui controles como:

- Senhas armazenadas com hash.
- Verificação de autorização por perfil no servidor.
- Proteção CSRF nas operações de alteração.
- Limitação de tentativas em fluxos de autenticação e confirmação sensíveis.
- CPF protegido por cifragem e apresentação mascarada conforme a tela.
- Verificações de titularidade dos pedidos e dos pontos.
- Validação de opções e preços dos produtos.
- Controle de duplicidade em operações financeiras e checkout.
- Cookies com `HttpOnly` e `SameSite`, com opção de `Secure` na implantação HTTPS.
- Verificação de versões/situação de acesso de administradores.
- Cabeçalhos de proteção e restrição de cache nas páginas dinâmicas.
- Migrações aditivas e backups nas rotinas específicas de atualização.

Esses controles fazem parte da implementação; não representam certificação ou auditoria externa de segurança.

**Preservar `instance/` é essencial:** além dos bancos, há chaves e configurações necessárias para ler dados protegidos e manter o funcionamento dos ambientes. A recuperação deve considerar bancos, arquivos, chaves e configurações em conjunto.

## Execução local

### 1. Obter o projeto e instalar dependências

```bash
git clone https://github.com/LovanGoulart/restaurante.git
cd restaurante
python -m venv .venv
```

**Windows — PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_geral.py
.\.venv\Scripts\python.exe run.py
```

**Linux ou macOS:**

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python setup_geral.py
.venv/bin/python run.py
```

O `setup_geral.py` solicita os dados do proprietário da plataforma e a criação da senha. Não é necessário divulgar uma credencial padrão no README.

### 2. Configurar o primeiro restaurante

1. Acessar `http://127.0.0.1:5000/geral/login`.
2. Entrar com a conta criada no terminal.
3. Cadastrar o restaurante, seu identificador e o administrador.
4. Definir o período de acesso.
5. Abrir o link do restaurante e entrar com o administrador cadastrado.
6. Configurar catálogo, equipe, identidade visual e operação de entrega.

Exemplos de rotas para um restaurante com identificador `kasarao`:

| Acesso | Endereço local |
| --- | --- |
| Administração geral | `http://127.0.0.1:5000/geral/login` |
| Login do restaurante | `http://127.0.0.1:5000/r/kasarao/login` |
| Cardápio público | `http://127.0.0.1:5000/r/kasarao/cardapio` |
| Entrada do salão | `http://127.0.0.1:5000/r/kasarao/salao` |

O identificador é definido no cadastro. A porta padrão de `run.py` é **5000**, podendo ser alterada pela variável `PORT`.

### 3. Configurar notificações Web Push

```bash
python setup_push.py
```

Utilize o Python do ambiente virtual, informe o contato solicitado, reinicie o sistema e ative os avisos nos dispositivos. O `run.py` inicia o servidor e um processo de trabalho para notificações. Em hospedagem, esses processos precisam de configuração e supervisão adequadas.

### 4. Atualizar instalações existentes

Antes de atualizar, faça backup consistente e preserve as pastas de dados de todos os restaurantes. Siga as instruções da atualização correspondente à versão instalada.

O `setup_geral.py` possui fluxo de adoção de um banco existente, sem substituição de seus registros. **Não utilize `init_db.py` como comando de atualização da plataforma.**

Para bases anteriores ao módulo de fidelidade, a migração específica é:

```bash
python migrate_loyalty.py
```

A rotina identifica bases SQLite compatíveis e cria as tabelas necessárias. A escolha de uma base específica também é suportada por `--banco`. A migração fiscal possui comandos próprios em `fiscal_cli.py`; deve ser utilizada conforme a configuração desse módulo.

### Configurações de ambiente

| Variável | Finalidade |
| --- | --- |
| `SECRET_KEY` | Chave da aplicação configurável; a plataforma também mantém chaves persistentes próprias. |
| `DATABASE_URL` | Conexão da aplicação/base padrão; os restaurantes da plataforma possuem suas configurações individuais. |
| `COOKIE_SECURE` | Usar `1` para cookies seguros na implantação com HTTPS. |
| `HOST` | Endereço de escuta do servidor local; padrão `127.0.0.1`. |
| `PORT` | Porta do servidor; padrão `5000`. |
| `FISCAL_PRODUCTION_ENABLED` | Habilitação explícita de produção fiscal, em conjunto com a configuração do módulo. |

## Testes e validação

O projeto possui testes automatizados para fluxos de plataforma, permissões, clientes, pedidos, entregadores, caixa, notificações e regras dos módulos disponíveis na versão.

Para executar a suíte:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Use o interpretador do ambiente virtual. A presença dos testes não equivale a garantir que todas as combinações de ambiente e todas as versões estejam homologadas.

Uma validação funcional deve percorrer:

1. Cadastro do restaurante e de usuários com diferentes perfis.
2. Pedido pelo PDV, preparo e entrega na mesa.
3. Entrada por QR Code, vinculação de comanda e novo pedido da mesma sessão.
4. Pedido online com retirada e com delivery.
5. Atribuição e conclusão da entrega e acerto do entregador.
6. Abertura, movimentos e fechamento do caixa.
7. Crédito de pontos, resgate e cancelamento permitido.
8. Consulta de finalizados, filtros e exportações.
9. Suspensão e renovação do acesso do restaurante.
10. Instalação PWA, som, vibração e Web Push em dispositivos reais.

## Evolução para SaaS

### Base já implementada

- Administração central de estabelecimentos.
- Identificador e endereço por restaurante.
- Separação de banco e arquivos por ambiente.
- Contas administrativas vinculadas ao estabelecimento.
- Planos com validade e renovação manual.
- Suspensão de acesso e registro de alterações.
- Personalização por restaurante.
- Perfis operacionais e recursos de relacionamento com clientes.

### Próximas etapas de produto e infraestrutura

- Automatizar contratação, cobrança recorrente e renovação com confirmação de pagamento.
- Estruturar onboarding e suporte para novos estabelecimentos.
- Validar capacidade e concorrência com testes de carga.
- Implantar monitoramento, logs operacionais e alertas de falhas.
- Automatizar backups e testar restauração por restaurante.
- Estabelecer política de retenção, privacidade e tratamento de dados.
- Organizar deploys, migrações e atualização segura de todos os ambientes.
- Avaliar evolução da persistência e da arquitetura conforme o crescimento.
- Homologar notificações, PWA e integração fiscal nos ambientes de destino.
- Ampliar testes automatizados e integração contínua.

### Limites atuais

- Os planos da plataforma são administrados manualmente.
- Os pagamentos dos pedidos são registrados e conferidos pela operação; não há conciliação bancária automática geral.
- A arquitetura e as transações atuais são orientadas a SQLite; migrar para outro banco exige adaptação e testes.
- O sistema não oferece envio de pedidos ou recebimentos offline.
- O delivery não inclui rastreamento GPS nem roteirização automática.
- Não há controle completo de estoque de ingredientes e ficha técnica.
- Integrações externas dependem de credenciais, disponibilidade e homologação específicas.
- Algumas consultas operacionais possuem limites de registros; relatórios, paginação e histórico atendem necessidades próprias de consulta.

## O que este projeto demonstra

O desenvolvimento reúne desafios de produto e engenharia presentes em aplicações de gestão:

- Traduzir regras de atendimento em fluxos diferentes para cada perfil.
- Relacionar mesa, comanda, cliente, pedido, produção, entrega e recebimento.
- Aplicar regras financeiras e de fidelidade no servidor.
- Organizar isolamento de dados para múltiplos estabelecimentos.
- Integrar comunicação em tempo real à operação.
- Preservar registros existentes durante a evolução do sistema.
- Construir interfaces responsivas para usuários com responsabilidades distintas.
- Produzir indicadores e exportações a partir dos dados operacionais.
- Preparar uma aplicação de gestão para evoluir como produto SaaS.

## Autor

Desenvolvido por **Lovan Anderson Goulart**, com apoio de ferramentas de inteligência artificial durante o desenvolvimento.

O projeto faz parte do meu portfólio de aplicações com Python e Flask e da minha evolução profissional em desenvolvimento de sistemas, automação e integração de serviços.

[Perfil no GitHub](https://github.com/LovanGoulart) · [Repositório do projeto](https://github.com/LovanGoulart/restaurante)
