# Cardápio por categorias e opções de produtos

## Atualizar a instalação existente

1. Pare o servidor e o processo de notificações.
2. Faça uma cópia de segurança do projeto atual, principalmente da pasta `instance` inteira.
3. Extraia o ZIP em uma pasta temporária. Dentro dele está a pasta `restaurante`.
4. Copie o código dessa pasta para seu projeto atual, substituindo os arquivos correspondentes. Preserve sua pasta `instance`, seu ambiente `.venv` e as variáveis de ambiente da hospedagem.
5. Inicie novamente o sistema. No PythonAnywhere, use Reload na aba Web e reinicie a tarefa de notificações se necessário.
6. Atualize o navegador com Ctrl+F5. Para o PWA já instalado, feche e abra novamente com internet.

Esta atualização não altera o esquema do banco. Não execute `init_db.py` nem `setup_geral.py` para aplicar apenas esta mudança. Se você já usa a versão atual com administração geral e restaurantes separados, suas contas e seus pedidos continuam os mesmos.

O ZIP não contém bancos, chaves ou fotos particulares da pasta `instance`. Mantenha essa pasta da instalação que você já utiliza.

## Onde o administrador configura

Abra **Gerenciar → Produtos**, confirme a senha e clique em **Opções do produto** no produto desejado. Cadastre o produto primeiro se ele ainda não existir.

Você pode usar os modelos:

- **Tamanhos de pizza:** Broto, Média e Grande. Edite os textos, a quantidade de fatias e os acréscimos de acordo com seu cardápio.
- **Bordas:** Sem borda, Requeijão e Chocolate. São exemplos editáveis; adicione ou remova sabores.
- **Ponto da carne:** Mal passado, Ao ponto e Bem passado.
- **Grupo personalizado:** escolha seu próprio título, como Molhos, Acompanhamentos ou Retirar ingredientes.

Os modelos não alteram preços automaticamente: os acréscimos começam em 0,00. Defina-os e salve.

## Tipos de opção

- **Uma escolha:** permite selecionar uma alternativa no grupo.
- **Várias escolhas:** permite selecionar várias alternativas até o limite definido pelo administrador. O preço soma o acréscimo de cada escolha selecionada.
- **Texto curto:** permite preencher uma informação de até 60 caracteres, com título definido pelo administrador.

Em cada grupo você pode marcar **Exibir este grupo** e **Preenchimento obrigatório**. Em cada escolha pode desmarcar **Exibir**, por exemplo para ocultar temporariamente um tamanho ou um sabor de borda. Para ocultar o produto inteiro, desmarque **Ativo** no cadastro normal do produto.

A observação livre tem configuração própria: você pode ativar ou desativar, mudar seu título e escrever a dica exibida no campo.

Use títulos e escolhas curtos. O resumo enviado para a cozinha, incluindo todas as opções e observações de cada linha, tem limite de 300 caracteres. Se ultrapassar, o sistema pede para resumir; o texto não é cortado silenciosamente.

## Exemplo de preço

Produto com preço base de R$ 50,00:

| Escolha | Acréscimo |
|---|---:|
| Média · 8 fatias | R$ 0,00 |
| Grande · 12 fatias | R$ 15,00 |
| Sem borda | R$ 0,00 |
| Borda de requeijão | R$ 5,00 |

Grande com requeijão custa R$ 70,00 por unidade. Duas unidades custam R$ 140,00.

O preço base é o cadastrado em Produtos. Os valores das escolhas são acréscimos, não preços finais. Os preços são novamente calculados no servidor ao enviar o pedido.

## Como o usuário faz o pedido

1. Escolhe uma categoria ou usa a busca.
2. Toca no produto, na imagem ou no sinal de adicionar.
3. Seleciona as opções, escreve a observação permitida e ajusta a quantidade.
4. Toca em **Adicionar**.
5. Confere a sacola e pode usar **Editar opções e observação** antes de enviar.
6. Finaliza pelo fluxo já existente: comanda e mesa no salão, ou retirada/entrega no cardápio do cliente.

As categorias aparecem antes dos respectivos produtos. No desktop, a sacola continua ao lado; no celular, use o botão **Ver pedido/Ver sacola**.

O mesmo componente funciona no PDV do administrador e do garçom, no cardápio do cliente e no pedido pelo QR Code. A cozinha continua sem acesso ao PDV e recebe as opções nos detalhes dos itens.

Cada inclusão gera uma linha na sacola, permitindo duas pizzas iguais com tamanhos ou bordas diferentes. A quantidade da linha representa unidades com as mesmas escolhas. O checklist continua aplicado à linha inteira do pedido.

## Dados e segurança

- Cada restaurante guarda suas próprias configurações em `instance` ou na pasta privada atribuída ao seu restaurante, em `product-options/<id>.json`.
- Inclua esses arquivos no backup da pasta privada, junto dos bancos, imagens e chaves.
- A área é restrita ao administrador e usa a mesma confirmação de senha da área Produtos.
- Escolhas obrigatórias, opções ocultas, limite de seleções e acréscimos são validados no servidor.
- Se o administrador alterar as opções enquanto existe uma sacola aberta, o pedido antigo pode pedir que o usuário atualize o cardápio e escolha novamente. O preço não é alterado silenciosamente em pedidos já enviados.
- Pedidos existentes guardam o preço e o resumo do momento do envio.
- A versão inclui os ajustes anteriores de checklist, busca do entregador, cabeçalho compacto do PDV e PWA da administração geral.

## Verificações

- 87 testes existentes do sistema passaram.
- 7 testes novos de opções passaram: preço e histórico, opções obrigatórias/ocultas, observações, permissões/CSRF, texto e múltiplas escolhas, telas e isolamento entre restaurantes.
- Teste de navegador: configuração pelo administrador, campos obrigatórios, tamanho oculto, preços, variantes separadas, edição, filtros, envio pelo administrador, cliente e QR Code, acesso do garçom e bloqueio da cozinha.
- Responsividade conferida em 320, 390, 850, 1024 e 1440 px.

As configurações dos exemplos de teste não são cadastradas nos seus produtos automaticamente.
