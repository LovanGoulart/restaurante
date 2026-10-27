# Restaurante Manager · versão 3.2 · salão, pedidos online e entregadores

Pedidos, cozinha e caixa em Python/Flask, SQLAlchemy e SQLite. Interface em português, navegação fixa e uso adaptado a celulares. Esta atualização mantém a estrutura do projeto anterior.


## Código organizado e formatado

Esta entrega mantém as funcionalidades da versão 3.2 e organiza o código-fonte com quebras de linha, indentação e espaçamento consistentes: Python com quatro espaços; HTML/Jinja, CSS, JavaScript e manifesto com dois espaços. O HTML gerado pelo JavaScript também foi dividido em blocos legíveis.

Para atualizar uma instalação que já está na versão 3.2, substitua os arquivos do código, preserve **instance/** e reinicie o servidor. Esta formatação não exige nova migração nem reinstalação das dependências da aplicação.

### Manter o padrão ao editar (opcional)

As ferramentas abaixo são apenas para desenvolvimento; o sistema continua iniciando normalmente com Python, sem precisar de Node.js.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m black .
```

Para formatar o frontend, com Node.js/npm instalados:

```powershell
npm install
npm run format:frontend
npm run check:format
```

A configuração inclui suporte a templates Jinja. Não use um formatador de HTML que interprete os blocos Jinja como HTML comum. Os comentários `/* HTML */` nos arquivos JavaScript identificam os trechos de interface para o formatador.

## Ajuste 3.2: entregador e acerto do dia

Esta versão acrescenta somente o fluxo de entregador e a conferência dos valores. A atualização a partir da versão 3.1 precisa criar a tabela nova `entrega`, preservando os dados anteriores.

### Atualizar a versão 3.1

Pare o sistema e faça backup da pasta `instance/`. Copie o código novo mantendo sua pasta `instance/`, abra o PowerShell na pasta do projeto e execute:

```powershell
.\.venv\Scripts\python.exe migrate.py
.\.venv\Scripts\python.exe run.py
```

A migração é aditiva, faz backup do SQLite e cria a tabela ausente. Não reinicialize o banco. Se a pasta nova ainda não tiver o ambiente `.venv`, siga os passos de criação do ambiente e instalação das dependências da seção de atualização abaixo. Reabra o PWA para receber os novos arquivos.

### Operação do entregador

1. Administrador: **Mais → Equipe**, crie o usuário com perfil **entregador** e deixe-o ativo.
2. Quando a tele-entrega ficar **pronta**, escolha o entregador no cartão do pedido e toque em **Enviar com entregador**. O pedido passa para **saiu para entrega** e aparece no dispositivo do responsável, com aviso em tempo real. O entregador só vê as tele-entregas atribuídas a ele; não acessa salão, retirada, clientes, PDV, caixa ou gestão.
3. O entregador recebe nome do destinatário, endereço, referência, contato se houver, itens, total, forma escolhida e informação de troco. CPF e nascimento não são exibidos.
4. Após entregar, toque em **Confirmar entrega e pagamento**, selecione a forma realmente recebida (dinheiro, Pix, crédito ou débito), marque a confirmação e conclua. O valor é calculado pelo servidor. A forma real fica no registro da entrega; a preferência original do cliente permanece preservada.
5. Se o administrador já registrou o pagamento, o entregador vê **Já pago / Não cobrar novamente**. A entrega é registrada como paga antecipadamente e o valor recebido pelo entregador é zero.
6. O registro do entregador não movimenta o caixa nem libera gestão financeira. O recebimento aguarda conferência do administrador. Uma entrega concluída não pode ser concluída ou reatribuída novamente.

O entregador pode consultar suas entregas concluídas por dia. As que ainda estão em andamento aparecem mesmo se vierem de dias anteriores. O administrador pode reatribuir uma entrega em andamento; ela deixa de aparecer para o responsável anterior. Entregadores com entregas em andamento não podem ser desativados ou ter seu perfil alterado antes de reatribuir esses pedidos.

### Conferência pelo administrador

Em **Mais → Acerto de entregadores**, escolha a data da entrega (horário de Brasília) e, se quiser, um entregador. O resumo informa:

- Número de entregas concluídas e total dos pedidos, incluindo a taxa de entrega.
- Total recebido pelo entregador e valores já conferidos.
- **Dinheiro a repassar**, líquido do troco, pendente de conferência.
- Pix, crédito e débito pendentes de conferência, separados do dinheiro físico.
- Pedidos pagos antecipadamente, que não geram uma segunda cobrança.

Para encerrar o acerto, selecione as entregas, toque em **Conferir selecionadas**, confira o dinheiro e os comprovantes e confirme. É necessário caixa aberto para registrar recebimentos ainda não pagos. O sistema gera um único movimento de recebimento por pedido, associa o acerto ao administrador e bloqueia repetição/duplicação. Um erro em qualquer entrega impede a gravação de todo o lote. Entregas apenas com pagamento antecipado podem ser conferidas sem novo movimento de caixa.

Depois da conferência, o saldo pendente correspondente diminui e o histórico continua visível. A data do filtro é a data de conclusão da entrega; a data do acerto fica registrada separadamente. O dinheiro passa a compor o saldo esperado do caixa quando o administrador confirma o acerto. Pix/cartões não são somados ao dinheiro físico.

Este saldo é o valor das vendas a conferir/repassar ao restaurante. Não calcula comissão, salário ou remuneração do entregador. Pix e cartões continuam com conferência manual; não há consulta automática a bancos ou operadoras. Os pedidos de entrega antigos sem entregador vinculado mantêm o fluxo administrativo anterior; passe a atribuir os novos pedidos para que entrem no resumo por entregador.

A versão acrescenta testes de permissões, atribuição/reatribuição, pagamentos antecipados, dinheiro/Pix/cartões, duplicação, lote atômico, fechamento por dia e migração da versão anterior. O fluxo atribuir → concluir no celular → conferir no caixa também foi verificado em navegador, com as telas novas adaptadas de 320 a 1280 pixels.

## Correção 3.1: celular e alerta sonoro

A correção remove a largura mínima que fazia a coluna do cardápio ultrapassar a tela. Grades, campos de data, cabeçalho, textos longos e sacola agora se ajustam ao espaço disponível. A rolagem horizontal de categorias fica contida na própria faixa, sem alargar a página.

O som é opcional e precisa de ativação em cada dispositivo/conta:

1. Toque em **Ativar som** no aviso da página, ou em **Mais → Ativar som dos avisos**.
2. Em **Mais → Testar alerta sonoro**, confira o aviso de três notas com o volume do aparelho ligado.
3. Após navegar ou reabrir o app, se aparecer **Liberar som**, toque para autorizar o áudio nesta tela. A preferência fica salva, mas o navegador pode exigir nova interação.

Com o sistema aberto, novos pedidos avisam cozinha/administrador e pedidos prontos avisam o responsável/administrador, conforme as permissões. Com o app fechado, os avisos Web Push usam o comportamento de som do sistema operacional; o tom personalizado não roda em segundo plano e o aparelho pode silenciá-lo por volume, modo silencioso ou Não Perturbe.

Para atualizar da versão 3 para a 3.1, substitua os arquivos do código, preserve **instance/** e reinicie o servidor. Não há mudança adicional no banco. Reabra o PWA ou recarregue a página para receber os novos arquivos. Para versões anteriores, siga a migração abaixo.

Verificação desta correção: 198 combinações de páginas/perfis/larguras entre 320 e 1280 pixels, sem rolagem horizontal da página no Chromium de teste; sacola de entrega também conferida. Alertas de cozinha e garçom foram exercitados por SSE em sessões separadas, com verificação do agendamento de áudio. O volume audível no alto-falante e o comportamento de cada aparelho real precisam ser conferidos com o botão de teste.

## Novidades da versão 3 e permissões

| Perfil | Acesso |
|---|---|
| Administrador | Gerencia equipe, produtos, categorias, clientes, configurações da loja, todos os pedidos, entregas, pagamentos, caixa e dashboard. |
| Entregador | Acessa somente tele-entregas atribuídas, confirma a entrega e informa a forma de pagamento recebida. Sem gestão do sistema ou caixa. |
| Cozinha | Consulta a fila ativa de pedidos do salão e online e altera apenas para em preparo e pronto. Sem PDV, caixa, equipe ou cadastros. |
| Garçom | Usa o PDV e acompanha os pedidos do salão. Registra a entrega dos pedidos prontos do salão. Sem pedidos online, clientes ou gestão. |
| Cliente | Consulta o cardápio, mantém a própria conta/endereço, faz pedidos online e acompanha somente os próprios pedidos. Sem acesso às telas internas. |
| Visitante | Consulta o cardápio público e monta a sacola; precisa de cadastro e login para confirmar um pedido. |

As permissões são verificadas no backend, inclusive quando a pessoa tenta acessar a URL ou chamar a API diretamente. Os links também são separados por perfil. Preferências de som, instalação, notificações e saída da conta continuam disponíveis para cada usuário.

## Como liberar pedidos de casa

1. Administrador: em **Mais → Loja e entregas**, configure o nome do restaurante, a taxa fixa de entrega e se aceita pedidos online e tele-entrega. A taxa inicial é R$ 0,00; ajuste antes de divulgar o link.
2. Compartilhe o endereço **`/cardapio`** do seu domínio HTTPS. Em teste no computador servidor, use http://127.0.0.1:5000/cardapio. `/login` atende clientes e equipe com os respectivos perfis.
3. O cliente escolhe produtos e quantidades e cria uma conta em `/cadastro`, com nome, login, senha, CPF e data de nascimento. Cadastro público sempre cria o perfil **cliente**; ele não pode escolher ser funcionário ou administrador.
4. Para retirada no caixa, não é solicitado endereço. Ao cadastrar ou pedir com tele-entrega, são obrigatórios rua/endereço, número (aceita s/n), bairro e referência (pode informar sem referência). Telefone é opcional.
5. O checkout permite retirada ou entrega, Pix, dinheiro, crédito ou débito; em dinheiro, pode informar o valor para troco. Produtos, taxa e total aparecem antes de confirmar.
6. A forma escolhida representa intenção de pagamento, não pagamento confirmado. O pedido nasce **não pago**. Apenas o administrador confirma o recebimento com caixa aberto.
7. Cozinha e administrador veem o pedido online. Ele é identificado como **Retirada no caixa** ou **Tele-entrega**, sem se passar por uma mesa. O garçom não vê esse pedido nem suas notificações.
8. Na cozinha: aberto → em preparo → pronto. O administrador confirma a retirada ou, na entrega, registra **saiu para entrega → entregue**. O cliente acompanha em `/meus-pedidos`, com atualização em tempo real e avisos do próprio pedido.

A sacola online guarda somente itens e preferências de modalidade/pagamento na sessão do navegador, preservando-os durante o login. Endereço, CPF e nascimento não entram no armazenamento offline do PWA. O pedido guarda uma cópia do endereço, do destinatário, da taxa e da forma escolhida; futuras alterações no cadastro ou na taxa não mudam pedidos já feitos. O total é calculado no servidor. Se o preço ou a taxa mudarem em relação ao cardápio aberto, a confirmação é bloqueada até atualizar.

### CPF e dados do cliente

A validação de CPF confere formato, 11 dígitos e dígitos verificadores, rejeita números repetidos e bloqueia cadastro duplicado. **Não consulta a Receita Federal, não verifica a situação cadastral e não prova que o CPF pertence ao cliente.** A data de nascimento precisa ser válida e não estar no futuro.

O CPF completo é cifrado com Fernet e associado a um hash autenticado para detectar duplicados. As telas exibem somente CPF mascarado. A chave fica em **`instance/customer-data.key`** e precisa acompanhar o backup do banco. Se a chave for perdida, restaure-a do backup; não gere outra para um banco com clientes. Endereços são visíveis ao próprio cliente e ao administrador; a cozinha recebe nome, modalidade e itens, sem CPF, nascimento ou endereço completo. Garçons não recebem dados de pedidos online.

A conta permite atualizar nome, endereço e senha; mudança de senha exige a senha atual. Alteração de CPF/login/nascimento e recuperação de senha por e-mail não estão implementadas. O administrador pode desativar/reativar uma conta em **Clientes**, sem transformá-la em conta de equipe. Defina os procedimentos de atendimento e privacidade do restaurante antes do uso público.

### Proteção do acesso público

Cadastro e login têm limites de tentativas registrados no banco (cadastro: 10 por hora por IP; login: 50 por 15 minutos por IP e 10 por login/IP). Registros de tentativas guardam um hash da chave de limitação, sem senha ou CPF. Se houver proxy, configure de forma controlada o IP real e os limites na infraestrutura; não confie em cabeçalhos enviados diretamente pelo visitante. Não há autenticação de CPF por provedor externo, geolocalização, cálculo por distância ou verificação automática da área de entrega. Nesta versão, a taxa é fixa e o restaurante precisa conferir a viabilidade do endereço.

## Atualizar a versão anterior sem perder dados

1. Pare o servidor e o worker antes da atualização.
2. Guarde uma cópia completa da pasta anterior, principalmente `instance/` (banco, chave de sessão e chaves push).
3. Extraia este ZIP em uma pasta nova. Copie a pasta `instance/` anterior para dentro de `restaurante_manager/` da versão nova. Não substitua seu banco por um banco de exemplos.
4. No PowerShell, abra a pasta nova que contém `app.py`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe migrate.py
.\.venv\Scripts\python.exe run.py
```

A migração cria somente as tabelas ausentes de notificações, clientes, loja, pedidos online, controle de envios e tentativas de acesso; não altera colunas das tabelas antigas. Faz backup do banco SQLite antes de criar tabelas e não modifica usuários, senhas, produtos, pedidos ou caixa. Não execute scripts de reset. Esta migração atende aos bancos das versões 1 e 2 entregues nesta conversa; outros esquemas devem ser comparados antes de atualizar.

## Instalação nova no Windows

Abra o PowerShell na pasta que contém `app.py`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe init_db.py
.\.venv\Scripts\python.exe run.py
```

Crie o nome, login e senha de administrador quando solicitado. Abra http://127.0.0.1:5000. Não existe senha padrão. A chave de sessão é gerada automaticamente em `instance/secret.key`.

Depois da instalação, o arquivo `INICIAR_WINDOWS.bat` inicia o sistema com um duplo clique. Mantenha a janela aberta; ela executa o servidor e o worker. Encerre com Ctrl+C.

## O que mudou

- Cabeçalho fixo em todas as telas. No celular, atalhos fixos na parte inferior para as tarefas do perfil.
- Paleta azul escuro, laranja, verde e azul; os estados também têm rótulos de texto.
- Botões de toque maiores, busca por produto, categorias e sacola que abre na parte inferior do celular.
- Mesa em destaque nos cartões de pedido, itens e observações legíveis, contadores por status e confirmação do recebimento.
- Central de notificações com contador de não lidas em todas as telas autenticadas.
- Atualização por conexão SSE, reconexão automática e consulta de recuperação a cada 30 segundos na lista de pedidos.
- Aviso visual e som opcional. Ative o som em **Mais → Ativar som dos avisos**; o navegador precisa de interação para liberar áudio.
- PWA: ícones próprios, manifesto, service worker, tela de falta de conexão e opção de instalação. Não armazena dados autenticados em cache.
- Web Push com fila persistida, retentativas e desativação de inscrições expiradas. Avisos de mais de 15 minutos ou de etapas já concluídas são descartados pelo worker. Ao sair da conta, o vínculo push daquele dispositivo é desativado.
- Dashboard considera o dia no horário de Brasília. Horários dos pedidos acompanham o fuso do navegador.

## Fluxo de uso

1. Administrador: em **Mais → Equipe**, cadastre garçom e cozinha. Ajuste categorias e produtos; os produtos iniciais são exemplos.
2. Abra o caixa com o fundo inicial.
3. Garçom: escolha os itens no cardápio, abra **Ver pedido**, informe a mesa e as observações e envie.
4. Cozinha: novos pedidos aparecem na fila; use **Iniciar preparo** e depois **Marcar como pronto**.
5. Garçom: o aviso de pronto chega em qualquer tela autenticada do sistema. Em **Pedidos**, registre a entrega.
6. Administrador: abra o recebimento do pedido, confira mesa/valor, escolha a forma e confirme somente após receber o dinheiro ou comprovar a transação.
7. Registre sangrias/suprimentos e feche o caixa com o dinheiro contado.

Use dispositivos ou perfis de navegador distintos para testar administrador, cozinha, garçom e cliente simultaneamente.

## Notificações: tela e dispositivo

### Com o sistema aberto

SSE funciona sem serviço externo de push. Alterações são consultadas no servidor aproximadamente a cada segundo e enviadas pela conexão persistente. Pedidos novos alertam cozinha e administradores; pedidos prontos alertam o garçom responsável e administradores. Os garçons acompanham todos os pedidos do salão e recebem atualizações da fila, mas o aviso de pronto é destinado ao responsável. Nenhum garçom recebe dados de pedidos online. Clientes recebem apenas atualizações e avisos de seus próprios pedidos. Status e pagamento continuam separados.

A central mantém os avisos mesmo se o usuário estava desconectado. Áudio depende da permissão de reprodução/interação e pode ser suspenso pelo navegador em segundo plano.

### Com o app fechado (Web Push)

Configure uma vez no servidor:

```powershell
.\.venv\Scripts\python.exe setup_push.py
```

Informe um e-mail real de contato do responsável pelo serviço. O script gera as chaves VAPID em `instance/vapid.json`, sem sobrescrever as existentes. Reinicie `run.py`.

Depois:

1. Publique o sistema em um domínio com **HTTPS válido**.
2. Abra o sistema no dispositivo e faça login.
3. Se desejar, instale o aplicativo.
4. Em **Mais**, toque em **Ativar avisos no dispositivo** e aceite a permissão do navegador.
5. Teste um pedido real de homologação, bloqueie a tela e finalize o preparo pela conta da cozinha.

`run.py` inicia o worker de push automaticamente. Se a hospedagem inicia apenas `app:app` com WSGI, mantenha `python push_worker.py` como processo supervisionado separado. Use **um worker push por instalação**. Sem worker ativo, a interface informa que o serviço está indisponível. Não há envio se o servidor estiver desligado.

Push depende de internet, suporte do navegador, permissões e restrições de bateria/sistema; não é garantia de entrega instantânea. Em iPhone/iPad compatíveis, instale pela Tela de Início e ative os avisos dentro do aplicativo instalado. A entrega real em Android/iPhone/Windows precisa de validação no domínio de implantação; os testes automatizados usam envio simulado, sem inscrição de um dispositivo real.

Os provedores push dos navegadores recebem a inscrição e o conteúdo cifrado do aviso; considere esse serviço na documentação de privacidade da implantação. Não registre endpoints ou chaves em logs.

## Instalação PWA

- Chrome/Edge compatíveis: botão **Instalar app** ou **Mais → Instalar aplicativo**. Quando o navegador libera o prompt, o botão abre a instalação nativa.
- Safari no iPhone/iPad: Compartilhar → Adicionar à Tela de Início. O sistema apresenta essas instruções.
- No modo instalado, a opção é ocultada. Um marcador local também evita repetir a sugestão após instalação detectada; o navegador pode não informar se um app foi instalado por outro caminho ou removido.
- O service worker e o push exigem HTTPS. `localhost`/`127.0.0.1` servem para desenvolvimento no próprio computador. Acesso pelo IP HTTP de outro dispositivo da rede não habilita PWA/push.
- Fora da rede, o aplicativo mostra uma tela de reconexão. Pedidos, recebimentos e alterações exigem conexão e **não entram em fila offline**.

## Acesso pelo celular na rede local

Para testar somente a interface e SSE na mesma rede:

```powershell
$env:HOST="0.0.0.0"
.\.venv\Scripts\python.exe run.py
```

No celular, use `http://IP-DO-PC:5000` (substitua IP-DO-PC pelo IPv4 do computador). Configure o firewall para a rede privada autorizada. Isso não substitui HTTPS para instalação e push. O endereço 127.0.0.1 no celular aponta para o próprio celular, não para o servidor.

## Hospedagem e operação

- Banco SQLite e arquivos de chaves precisam de disco persistente. Não inclua `instance/` no Git ou em um ZIP público. Faça backups automáticos e teste restauração.
- Use HTTPS, `COOKIE_SECURE=1` e uma `SECRET_KEY` persistente. Variáveis são lidas do ambiente do processo; um arquivo `.env` não é carregado automaticamente.
- `run.py` usa Waitress com 64 threads. Cada conexão SSE utiliza uma thread; dimensione para o número de dispositivos e abas. Esta configuração destina-se a uma operação pequena, sem validação de carga comercial.
- Atrás de Nginx, desabilite buffering/cache para `/api/eventos` e configure timeout de leitura acima de 30 segundos. Exemplo:

```nginx
location /api/eventos {
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 60s;
}
```

- A hospedagem deve permitir conexões HTTP persistentes e processo de worker. Algumas plataformas limitam streams ou suspendem processos.
- O servidor de desenvolvimento `app.py` é útil para diagnóstico; prefira `run.py` ou um WSGI configurado para o uso operacional.
- Antes de venda/produção: valide o ciclo no restaurante, os aparelhos, a rede, a capacidade simultânea, o tratamento de perda de conexão, backups e proteção contra tentativas repetidas de login. A versão não inclui suporte contratado, homologação fiscal ou garantia operacional.

## Limites funcionais

Pagamentos são registros manuais integrais com uma forma por pedido. Não há integração bancária, pagamento dividido, emissão fiscal, estoque, roteirização de entregas ou adicionais complexos. A fila operacional consulta os 200 pedidos mais recentes; relatórios históricos/paginação avançada não foram implementados. O recebimento duplicado de um mesmo pedido é bloqueado. O checkout online usa uma chave de envio para impedir duplicação ao repetir a mesma tentativa após falha de conexão. No PDV do salão, confira a lista antes de reenviar uma tentativa cuja resposta se perdeu.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

A suíte também cobre cadastro de cliente, CPF/data, endereço condicional, isolamento de pedidos, taxa e snapshot de endereço, checkout idempotente, troco e fluxo completo de tele-entrega. A suíte verifica o ciclo pedido/preparo/entrega/pagamento/caixa, permissões, CSRF, SSE e replay, isolamento das notificações, inscrição e fila push com envio simulado, logout, arquivos PWA, chaves VAPID e migração com preservação dos dados. Não substitui testes reais em celulares, instalação PWA ou entrega pelos provedores externos.
