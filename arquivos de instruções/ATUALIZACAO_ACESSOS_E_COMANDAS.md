# Atualização — administradores, comandas e pedidos por QR Code

Esta atualização usa a versão com Administração Geral e restaurantes separados. Não cria outra tela inicial nem altera as regras de caixa, pagamento ou acerto de entregadores fora do escopo solicitado.

## 1. Como atualizar um sistema existente

1. Pare a aplicação e o worker de notificações durante a atualização. No PythonAnywhere, faça a atualização em uma janela sem operação e use Reload após concluir.
2. Faça uma cópia completa da pasta do projeto, principalmente de `instance`. Preserve bancos, fotos, chaves e configurações. Este ZIP contém somente código e instruções.
3. Copie os arquivos do ZIP sobre o projeto atual. Preserve seu `config.py` se ele contém caminhos específicos da hospedagem, mantendo a função `data_dir` e as demais configurações presentes nesta versão. Preserve também suas variáveis de ambiente e o arquivo WSGI.
4. No terminal, dentro da pasta que contém `app.py`, ative o mesmo ambiente virtual utilizado pelo servidor e execute:

```bash
python -m pip install -r requirements.txt
python atualizar_sistema.py
```

5. Reinicie a aplicação e o worker, ou dê Reload no PythonAnywhere. Para executar localmente:

```bash
python run.py
```

**Não execute `init_db.py` para atualizar bancos existentes. Não apague `instance` e não substitua seus bancos por arquivos de teste.**

O script `atualizar_sistema.py` percorre os restaurantes cadastrados, inclusive inativos, adiciona os campos necessários e cria um backup SQLite antes de cada alteração de esquema. É seguro executá-lo novamente: quando o esquema já está atualizado, ele não aplica outra alteração.

A base central de administradores recebe campos adicionais de forma aditiva quando é aberta. O backup completo de `instance` deve ser feito antes de iniciar esta versão, pois ele também protege a base central e todas as chaves. Para reverter, pare o serviço e restaure o código anterior junto com a cópia completa de `instance`.

Se a atualização indicar erro, resolva-o antes de abrir o sistema para atendimento. Em uma instalação nova sem conta geral, use `python setup_geral.py` e depois `python run.py`. Os novos restaurantes são inicializados pelo próprio painel geral.

## 2. Login e cadastro de administradores

### Administrador geral

Abra `/geral/login` e use **o e-mail cadastrado e a senha**, em vez do login antigo. Nenhuma senha é enviada por e-mail.

Se não lembrar o e-mail ou precisar corrigir a conta geral, execute no terminal do servidor:

```bash
python setup_geral.py --redefinir
```

Esse comando solicita nome, e-mail e nova senha, preserva restaurantes e pedidos, e encerra as sessões antigas do proprietário. Use-o apenas se precisar redefinir a sua conta; ele não é uma etapa obrigatória da atualização.

### Novo restaurante

No painel geral, preencha:

| Campo | O que informar |
| --- | --- |
| Nome do restaurante | Nome comercial exibido na operação. |
| Link do restaurante | Apenas um identificador, como `sabor-da-casa`. Não digite rua, `https://` ou um endereço completo. Ele gera `/r/sabor-da-casa/`. |
| Nome completo do administrador | Nome da pessoa que administrará o caixa. Substitui o antigo campo de login. |
| E-mail de acesso | E-mail pelo qual esse administrador entrará no sistema. Deve ser exclusivo entre os administradores desse restaurante. |
| CPF | CPF com 11 dígitos e dígitos verificadores corretos. A máscara é aplicada na tela. |
| Data de nascimento | Data válida entre 1900 e hoje, selecionada pelo calendário do dispositivo. |
| Endereço, número e bairro | Endereço do administrador. Use `s/n` se o imóvel não tem número. |
| Senha inicial | De 10 a 256 caracteres. Informe ao titular pelo meio que vocês utilizam; o sistema não envia mensagens. |
| Período de acesso | 1 mês, 3 meses, 6 meses ou 1 ano. |

Clique em **Cadastrar e liberar acesso**. Os erros aparecem no próprio formulário, mantendo os campos preenchidos para correção. Se a criação falhar por um problema interno, o cadastro incompleto é desfeito e pode ser tentado novamente. O código não consegue corrigir falta de permissão de gravação do servidor: a pasta `instance` precisa ser gravável pelo processo da aplicação.

Para incluir outros administradores do mesmo restaurante, abra **Administradores → Adicionar administrador neste restaurante**. Eles compartilham o plano do restaurante. Somente o administrador geral cria, ativa, desativa e renova esses acessos.

### Administradores já cadastrados

Abra **Administradores**, revise os dados pessoais e salve. O administrador do caixa passa a entrar pelo e-mail exibido nesse cadastro, mesmo que anteriormente usasse outro nome de login. Usuários da equipe e clientes com conta continuam com seus acessos atuais.

CPFs dos administradores são armazenados cifrados na base central, com chave em `instance/plataforma/administrator-data.key`. Preserve esse arquivo junto com a base. A validação de CPF confere os dígitos; não consulta a Receita Federal. A validação de e-mail confere o formato, sem envio de confirmação ou verificação da titularidade da caixa postal.

## 3. Mesa, comanda e inclusão de itens

O PDV agora mostra campos separados para **número da comanda** e **número da mesa**. Ambos aceitam somente números, até 12 dígitos; zeros à esquerda não criam uma comanda diferente (`008` e `8` são a mesma).

- Mesma comanda ainda não paga + mesma mesa: o sistema acrescenta os itens ao pedido existente e mantém o mesmo identificador.
- Mesma comanda ainda não paga + mesa diferente: o envio é bloqueado e a mesa já vinculada é informada.
- Mesma mesa + comandas diferentes: permitido; cada comanda tem sua conta e pagamento.
- Comanda paga: não aceita mais itens. Um novo atendimento pode reutilizar o número em outra comanda, mantendo o histórico já pago.

Nos detalhes de um pedido de salão, o botão **+ Adicionar itens à comanda** abre o PDV com comanda e mesa preenchidas. Escolha os produtos novos e envie. O sistema não reapresenta esses itens como uma segunda conta para recebimento.

Ao acrescentar itens, o pedido volta à fila de preparo para os novos itens. Cada item mantém sua etapa anterior: itens já prontos ou entregues continuam identificados dessa maneira nos detalhes, para orientar a cozinha. O status principal representa a etapa do conjunto da comanda.

Reenvios com a mesma chave de envio não acrescentam itens duas vezes. Se houver falha de conexão, confira a comanda antes de montar outro envio.

O antigo campo `mesa` no banco era utilizado como código da comanda. Ele foi preservado para evitar alterar históricos. O novo número físico da mesa fica no campo `numero_mesa`. Em pedidos antigos esse novo campo começa vazio: ao adicionar itens pela primeira vez, preencha a mesa correta. Pedidos antigos já duplicados não são reunidos automaticamente, pois podem ter recebimentos distintos.

## 4. Áreas protegidas no administrador do caixa

Pedirão a senha do administrador autenticado:

- Relatórios de vendas, inclusive download de planilhas.
- Loja e entregas.
- Categorias.
- Produtos.
- Equipe.
- Clientes, inclusive exportação de leads.

Ao clicar no menu, a tela **Confirme sua senha** será exibida. A conferência acontece no servidor: abrir uma URL diretamente ou chamar uma exportação também exige autorização para aquela área.

Cada liberação vale **5 minutos somente para a área escolhida**, permitindo salvar formulários e baixar a planilha sem perguntar a senha em cada requisição. Clicar novamente no menu protegido exige a senha novamente. Use **Bloquear áreas de gestão** ou saia da conta para encerrar as liberações antes do prazo. Não compartilhe a senha administrativa com funcionários.

Em **Gerenciar**, os cadastros protegidos ficam abaixo de **Personalização e fotos** e acima de **Ver cardápio público**. Relatórios permanece na navegação principal (e na barra de navegação do celular), sem repetir o link em Gerenciar.

## 5. Pedido presencial sem senha por QR Code

No administrador do caixa, abra **Gerenciar → QR Code para pedidos no salão**. Baixe a imagem SVG para impressão. Gere o código acessando o sistema pelo endereço público correto, preferencialmente com HTTPS. Um código criado com `localhost` ou `127.0.0.1` não serve para os celulares dos clientes.

Fluxo:

1. O cliente lê o QR Code, que abre `/r/<identificador>/salao`.
2. Ele informa seu nome e o número da mesa, ambos obrigatórios, sem cadastro, CPF, e-mail ou senha.
3. O sistema cria uma sessão individual aleatória naquele navegador; não há uma conta compartilhada por todos os clientes.
4. O cliente escolhe os itens e envia para a cozinha.
5. Cozinha, administrador e garçons recebem o pedido de salão com a mesa informada, inicialmente como **Aguardando comanda**.
6. O cliente acompanha somente os próprios pedidos em **Meus pedidos**, com atualizações e notificações do fluxo existente.
7. Ao atender a mesa, o garçom abre os detalhes, confere a **mesa** já preenchida, informa a **comanda** e clica em **Definir comanda e mesa**.
8. Se essa comanda já está aberta na mesma mesa, os itens são reunidos nela. Se pertence a outra mesa, a vinculação é bloqueada.
9. Quando o pedido está pronto e a comanda já foi vinculada, o garçom usa **Registrar entrega**. O administrador registra o pagamento no fluxo habitual.

O cliente não escolhe uma comanda de outra pessoa e não tem acesso à lista geral do restaurante. Se dois clientes forem vinculados à mesma comanda, cada navegador continua vendo **somente seus itens e seu subtotal**, enquanto o administrador vê a conta completa. O status principal e a situação de pagamento acompanham a comanda compartilhada.

O acesso sem senha depende da sessão do navegador: ao sair, limpar cookies ou trocar de navegador, o cliente perde acesso ao histórico dessa sessão. Abrir o link em outro aparelho cria outra sessão; não recupera os pedidos anteriores. O QR Code facilita o acesso ao link; ele não comprova presença física no restaurante.

Os pedidos de casa continuam usando o cardápio público e o cadastro habitual, com retirada ou tele-entrega. O acesso por QR Code desta atualização é exclusivamente presencial.

## 6. Verificações

Os testes usam bancos temporários. Não é necessário alterar dados de produção para validar a instalação.

```bash
python -m unittest discover -s tests -v
```

As verificações cobrem cadastro e validações, autenticação por e-mail, planos e isolamento entre restaurantes, senha das áreas administrativas, comandas, reenvios, pedidos por QR Code, privacidade e migração aditiva. A interface também foi verificada em navegador entre 320 e 1440 pixels.

Notificações visuais com o sistema aberto utilizam o fluxo existente. Web Push em segundo plano continua dependendo das chaves VAPID, do worker em execução, de HTTPS e da autorização do dispositivo. Esta entrega não incluiu envio real de push externo nem teste na sua hospedagem PythonAnywhere.
