# Atualização aplicada ao restaurante.zip enviado

Este pacote foi montado a partir do ZIP enviado nesta solicitação. Foram preservados os arquivos fora do escopo dos seis ajustes, incluindo cadastro_alimentos.py, imagens, textos dos menus e a tela de acerto dos entregadores. O banco existente deve ser mantido na sua instalação.

## Instalação

1. Pare a aplicação e os workers e faça backup completo, principalmente da pasta `instance`.
2. Copie o conteúdo da pasta `restaurante` deste ZIP sobre o código existente. Preserve `instance`, imagens, chaves e variáveis de ambiente.
3. Na pasta que contém `app.py`, com seu ambiente virtual ativado, execute:

```bash
python -m pip install -r requirements.txt
python atualizar_sistema.py
```

4. Só depois reinicie aplicação e workers. No PythonAnywhere, clique em **Reload** na aba Web.
5. Reabra o aplicativo ou atualize a página para carregar os scripts novos.

**A migração acima é obrigatória nesta atualização.** Ela acrescenta campos às bases cadastradas e cria backup SQLite antes de alterar cada base. Pode ser executada novamente. Não execute `init_db.py` nem substitua seu banco.

Para reverter, pare os processos e restaure juntos o código anterior e o backup completo anterior à atualização.

## Catálogo

Categorias e produtos têm botão **Excluir** com confirmação. Produtos excluídos saem do catálogo, preservando o histórico dos pedidos. Uma categoria só pode ser excluída depois que seus produtos forem excluídos ou movidos. Salvar as opções retorna à listagem de produtos.

## Segurança dos menus

Abra **Painel de Controle → Segurança dos menus**. Para deixar as áreas desbloqueadas, desmarque **Exigir senha adicional nos menus administrativos**, confirme sua senha e salve. A preferência vale para os administradores daquele restaurante; login e perfil de administrador continuam obrigatórios.

Mantendo a proteção ativa, cada área é liberada uma vez por sessão, sem prazo de expiração durante a edição. Para reativar a exigência, marque novamente a preferência e salve. O comando de bloquear áreas apenas limpa as liberações da sessão, sem alterar essa preferência. O vencimento do plano do restaurante continua seguindo as regras existentes.

## Pizzas

Configure exatamente um grupo ativo do tipo **Tamanhos de pizza** e um do tipo **Sabores da pizza (média)**. No primeiro cadastre tamanhos, fatias, acréscimo e máximo de sabores. No segundo cadastre os sabores com preços de pizza inteira. Para massas e adicionais use grupos personalizados; inclua a palavra “massa” no título do grupo de massas. Os limites e a obrigatoriedade são definidos nas opções do produto.

O catálogo exibe cards dos tamanhos configurados, com preço inicial. O fluxo percorre apenas as etapas existentes: massas, bordas, sabores, adicionais e observação. Produtos comuns mantêm seu fluxo anterior. Cada produto configurado como pizza gera seus próprios cards de tamanhos.

O valor é a média dos preços inteiros dos sabores escolhidos, mais os acréscimos de tamanho e opções. O servidor recalcula o pedido. O preço inicial considera o sabor mais barato e as opções obrigatórias mínimas.

Quantidade maior que um gera pizzas com escolhas independentes. Complete cada unidade pelas abas e pelo botão de avançar. A sacola tem editar, remover e continuar comprando, com opções agrupadas. O limite existente de texto combinado de opções e observação permanece em 300 caracteres por item; use nomes curtos nas escolhas.

## Notificações ao ficar pronto

- Tele-entrega: **Seu pedido está indo até você.**
- Retirada: **Seu pedido está pronto. Você pode ficar a vontade para vir retirar! Vem rapidinho para não esfriar viu!**
- Salão: **Seu pedido está pronto.**

O aviso de tele-entrega ocorre quando a cozinha marca como pronto, conforme solicitado. A confirmação efetiva da entrega continua com o entregador. Push externo depende das permissões do navegador e do worker configurado.

## Verificação

131 testes de backend aprovados. Verificado no navegador: retorno após salvar, liberação dos menus, tamanhos no catálogo, etapas obrigatórias, edição e remoção, duas pizzas com escolhas e valores independentes e uso móvel por cliente e garçom. A migração também foi executada em cópias das três bases de restaurante do ZIP: os campos e registros originais foram preservados e uma segunda execução não repetiu alterações. A hospedagem e o banco de produção não foram alterados.
