# Configuração de pizzas: conferência e proposta de interface

## Resultado da conferência do código atual

A tela não atende integralmente aos cinco requisitos. O cadastro da imagem foi implementado nesta atualização. As regras novas de preço descritas abaixo são uma proposta e não foram ativadas nesta entrega.

| Requisito | Situação atual | O que falta |
|---|---|---|
| Nome, descrição e categoria do produto | Disponível no cadastro de Produtos. Agora também há seleção de imagem, prévia, troca e remoção. | Nada para esse requisito. |
| Tamanhos e máximo de sabores por tamanho | Disponível. Cada tamanho tem nome, fatias, limite de sabores e acréscimo. | Preço base independente para cada tamanho. Atualmente o campo é um acréscimo à média dos sabores. |
| Massa obrigatória, seleção única e custo extra | Disponível. O administrador define uma opção por pedido e se o cliente precisa escolher. Há preço adicional por opção. | É necessário manter “Cliente precisa escolher” ativo e “Escolhe uma opção” no bloco de Massas. |
| Borda opcional, seleção única ou múltipla | Disponível com essas modalidades e limite para seleção múltipla. | Preço adicional diferente por tamanho. Hoje cada borda tem um acréscimo único. |
| Cobrança pela média ou pelo sabor mais caro | Somente a média está implementada. | Seletor de regra, cálculo pelo maior preço no servidor e na prévia do navegador. |

**Regra realmente usada hoje:** média dos preços inteiros dos sabores + acréscimo do tamanho + massa/borda/adicionais selecionados. O preço do produto base não é somado novamente à média. Assim, “preço base do tamanho” não deve ser confundido com o acréscimo atual.

A análise foi feita principalmente nas funções `clean_config`, `resolve_item` e `size_cards` de product_options.py e na prévia de preços de static/js/product-picker.js. O sistema recalcula no servidor; o valor informado pelo navegador não determina o preço final.

## Arquitetura de informação proposta

Usar um editor com seis seções numeradas. No desktop, uma navegação lateral curta; no celular, uma lista de etapas. Mostrar uma seção por vez, com resumo das demais. O botão Salvar permanece acessível, e um erro abre a seção e aponta o campo correspondente.

| Ordem | Seção | Pergunta respondida |
|---|---|---|
| 1 | Produto e imagem | O que estou vendendo? |
| 2 | Tamanhos | Quais tamanhos existem e quantos sabores cada um aceita? |
| 3 | Sabores e ingredientes | Quais sabores podem ser escolhidos e quanto custam? |
| 4 | Massas, bordas e acompanhamentos | O que é obrigatório, opcional e cobrado à parte? |
| 5 | Regra de cobrança | Como calcular uma pizza com vários sabores? |
| 6 | Revisão e simulação | O cliente verá a configuração correta e pagará o valor esperado? |

Essa navegação é uma proposta para os requisitos novos. A tela existente continua usando os blocos separados já implementados; o patch não substitui esses blocos por uma navegação ainda incompleta.

## Wireframe textual detalhado

### Cabeçalho do editor

**Configurar pizza — Pizza da casa**

Indicadores: Ativo no cardápio · Alterações não salvas.

Ações: Voltar para Produtos · Salvar configuração.

Resumo lateral: 3 tamanhos · 8 sabores ativos · Massa obrigatória · Borda opcional · Cobrança pela média.

### 1. Produto e imagem

| Campo/ação | Exemplo visual |
|---|---|
| Nome | Pizza da casa |
| Descrição do produto | Pizza artesanal preparada na hora. |
| Categoria | Pizzas |
| Imagem | Prévia da foto + Escolher imagem + Remover imagem |
| Disponibilidade | Exibir no cardápio |

A descrição geral apresenta a linha de produtos. Ingredientes específicos ficam nos sabores. Uma foto não deve ser condição para cadastrar ou salvar o produto.

**Implementado nesta entrega:** o campo Ícone e a grade de emojis foram removidos do cadastro. O usuário escolhe JPG, PNG ou WebP de até 5 MB, visualiza uma prévia e salva junto com o produto. A imagem aparece no catálogo e no PDV. A personalização existente continua funcionando sobre as mesmas imagens.

### 2. Tamanhos

Botões rápidos: Adicionar Broto · Adicionar Média · Adicionar Grande · Outro tamanho.

| Ativo | Tamanho | Fatias | Preço base do tamanho | Máx. sabores | Ações |
|---|---|---:|---:|---:|---|
| Sim | Broto | 4 | R$ 35,00 | 1 | Editar / Remover |
| Sim | Média | 8 | R$ 60,00 | 2 | Editar / Remover |
| Sim | Grande | 12 | R$ 80,00 | 4 | Editar / Remover |

Os valores acima são exemplos para o projeto da interface, não alterações de preços reais.

Um aviso deve distinguir limite e variedade: “Grande permite até 4 sabores; existem 2 sabores ativos. Cadastre mais sabores para oferecer as 4 escolhas distintas.” O limite configurado não deve ser substituído silenciosamente.

**Pendente:** trocar o atual modelo de acréscimo por um preço base independente exige uma mudança explícita na precificação. Não basta renomear a coluna, pois isso faria o preço informado significar outra coisa.

### 3. Sabores e ingredientes

Barra: Buscar sabor · Adicionar sabor.

Cada sabor abre uma ficha simples:

| Campo | Exemplo |
|---|---|
| Nome | Calabresa |
| Ingredientes | Molho de tomate, muçarela, calabresa e cebola. |
| Visibilidade | Disponível para escolha |
| Preço completo por tamanho — proposta | Broto R$ 35,00 / Média R$ 60,00 / Grande R$ 80,00 |

Na proposta, o preço completo de um sabor naquele tamanho pode substituir o preço base do tamanho. Quando não há substituição, usa-se o preço base. A interface deve chamar esse campo de “Preço da pizza inteira neste tamanho”, sem misturá-lo com “Acréscimo”. Não somar o preço base novamente depois de calcular a média ou o maior preço.

**Já disponível:** nome, descrição dos ingredientes e um preço inteiro por sabor. Preços de sabor separados por tamanho também não existem ainda no modelo atual.

### 4. Modificadores

Usar três cartões independentes, sem mostrar identificadores ou nomes técnicos de tipos.

**Massas**

- Exigir escolha: Sim.
- Quantas pode escolher: Uma.
- Linhas: Tradicional / R$ 0,00; Integral / R$ 3,00; Pan / R$ 5,00.
- Ações: Adicionar massa, ocultar e remover.

**Bordas recheadas**

- Oferecer bordas: Sim.
- Escolha obrigatória: Não.
- Seleção: Uma borda ou várias, com limite configurável.
- Se for seleção única opcional, o cliente pode continuar sem borda. Não selecionar uma borda paga por padrão.

| Borda | Broto | Média | Grande | Ações |
|---|---:|---:|---:|---|
| Catupiry | R$ 4,00 | R$ 6,00 | R$ 9,00 | Editar / Remover |
| Cheddar | R$ 4,00 | R$ 7,00 | R$ 10,00 | Editar / Remover |

Exibir a explicação: “Valores adicionados ao total da pizza. Informe 0,00 se não houver custo.” Uma célula vazia deve pedir definição ou assumir uma regra de herança claramente indicada, nunca uma interpretação silenciosa.

**Acompanhamentos e adicionais**

- Nome do bloco: Adicionais.
- Escolha obrigatória: Não.
- Máximo de opções: 2.
- Itens: Bacon, Queijo extra, Molhos.
- Cada item tem nome, descrição, preço adicional e visibilidade.

**Disponível hoje:** configuração de obrigatoriedade, seleção única/múltipla, limites e acréscimo único por opção. **Pendente:** matriz de preços por tamanho.

### 5. Cobrança fracionada

Campo visível: “Quando houver mais de um sabor, cobrar por:”

- Média dos sabores.
- Valor do sabor mais caro.

Prévia comparativa, para uma Média com sabores de R$ 60,00 e R$ 70,00:

| Regra | Pizza | Borda de R$ 6,00 | Total |
|---|---:|---:|---:|
| Média | R$ 65,00 | R$ 6,00 | R$ 71,00 |
| Mais cara | R$ 70,00 | R$ 6,00 | R$ 76,00 |

A regra deve usar os preços completos dos sabores para o tamanho escolhido. Massa, borda e adicionais entram depois e apenas uma vez por pizza. Para várias pizzas, cada unidade tem sabores e cálculo próprios.

**Pendente:** esse seletor e a regra “mais cara” ainda precisam de implementação. A entrega de imagens não modifica a regra atual da média.

### 6. Revisão e simulação

Mostrar um resumo legível, e não JSON ou tipos internos:

“Cliente escolhe o tamanho → massa obrigatória → borda opcional → até N sabores → adicionais → observação.”

Simulador: selecione tamanho, massa, borda e sabores e veja o detalhamento de pizza, modificadores, quantidade e total. Avisos devem abrir o bloco que precisa de correção.

Ações finais: Salvar configuração · Voltar e continuar editando.

## Lógica recomendada para a próxima implementação

- Conservar IDs dos tamanhos, sabores e modificadores ao editar.
- Usar centavos inteiros e arredondamento definido para a média.
- Validar tamanho, sabores ativos, quantidade, limites e preços no servidor.
- Registrar no pedido uma cópia do preço e das escolhas, para que alterações no cardápio não modifiquem pedidos antigos.
- Manter a mesma regra na prévia e no cálculo final; nunca confiar no total enviado pelo navegador.
- Para o modelo novo, armazenar preço base por tamanho, preços completos dos sabores por tamanho, preços dos modificadores por tamanho e regra de cobrança.
- Preservar configurações legadas no modelo de média + acréscimo até uma conversão explícita pelo administrador. Não converter preços automaticamente nem reinterpretar o campo atual de acréscimo.

## Escopo exato deste patch

Implementado: escolha da imagem no cadastro de produtos, prévia, troca, remoção, miniatura na listagem e manutenção da foto no PDV. Validação do arquivo no servidor e compensação da imagem se a gravação do produto falhar.

Não implementado nesta entrega: preço base independente por tamanho, preço da borda por tamanho, preço do sabor por tamanho e regra “mais cara”. Esses pontos foram auditados e projetados acima, atendendo à solicitação de conferência e wireframe sem mudar silenciosamente a cobrança existente.
