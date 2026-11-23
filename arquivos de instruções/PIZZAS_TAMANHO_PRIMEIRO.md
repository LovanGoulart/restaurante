# Correção do fluxo de pizzas — tamanho primeiro

Esta versão mantém a última base restaurante.zip enviada e a correção do cadastro_alimentos.py.

## Aplicar

1. Pare a aplicação e os workers e faça backup completo.
2. Copie o conteúdo da pasta restaurante deste ZIP sobre o código atual. Mantenha sua pasta instance inteira: banco, imagens, opções, chaves e configurações.
3. Se ainda não aplicou a atualização anterior de exclusão/menus, execute `python atualizar_sistema.py` no ambiente virtual. Quem já executou não precisa de nova migração para esta correção de pizzas.
4. Reinicie a aplicação e o worker. Atualize a página com Ctrl+F5 ou feche e reabra o PWA.

## Como pedir

O catálogo de pizzas começa com os TAMANHOS disponíveis. Clique no tamanho para continuar: massas, bordas, sabores, adicionais e observação. Somente etapas configuradas pelo administrador aparecem. Na última etapa, Inserir adiciona à sacola. A sacola tem Editar, Remover e Continuar comprando.

Se a pizza for aberta por uma entrada sem tamanho, o seletor exige escolher o tamanho primeiro; não escolhe automaticamente o primeiro da lista. Quantidade maior que um permite personalizar cada pizza separadamente. O valor continua sendo a média dos sabores mais os adicionais definidos.

## Pizzas importadas pelo cadastro_alimentos.py

Esses cadastros eram produtos simples e não tinham os grupos necessários ao fluxo de pizza. Agora eles também aparecem por tamanho e os sabores do mesmo tamanho são agrupados. A descrição dos itens demonstrativos informa Grande · 8 fatias; por isso esse é o tamanho inicialmente exibido. Se o cadastro não informar tamanho, será mostrado Tamanho único. Não são inventados preços de tamanhos ou de bordas.

**Para oferecer Pequena, Média, Grande e Família**, abra Produtos → Opções do produto em uma das pizzas desse conjunto. A tela já apresenta os grupos de tamanho e sabores:

- Em Tamanhos de pizza, adicione os tamanhos, a quantidade de fatias no nome, o acréscimo e o máximo de sabores de cada tamanho.
- Em Sabores da pizza (média), confira os preços inteiros dos sabores.
- Adicione Massas, Bordas e Adicionais somente se desejar oferecê-los. Configure a obrigatoriedade e os limites. O título do grupo de massas deve conter a palavra massa.
- Salve. Os tamanhos passam a aparecer como cards, antes da escolha de sabores. Os cadastros simples representados nesse conjunto não reaparecem como cards de sabores separados.

Os tamanhos, limites, preços e grupos que já estavam configurados são preservados. Configurações idênticas não repetem os mesmos cards. Configurações diferentes continuam sendo conjuntos distintos.

Produtos fora das categorias de pizza mantêm o fluxo anterior. Pedidos antigos não são modificados.

## Verificação

136 testes automatizados aprovados. Fluxo conferido em navegador no desktop e celular: tamanho obrigatório na entrada sem tamanho, seleção por etapas, duas pizzas independentes, edição/remoção, preços e pizzas simples importadas agrupadas por tamanho.
