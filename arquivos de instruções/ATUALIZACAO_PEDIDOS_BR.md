# Atualização de Pedidos, campos brasileiros e ícones

Preserve a pasta instance da sua instalação (banco, chaves, fotos e personalização). Faça backup antes de copiar os arquivos deste pacote. Não é necessário migrar nem recriar o banco. Reinicie a aplicação após atualizar. No PythonAnywhere, use Reload na aba Web. Reabra o PWA para receber o service worker atualizado.

## Pedidos como tela inicial
O administrador entra diretamente em /pedidos, com o título Pedidos. A tela /inicio foi descontinuada e redireciona para Pedidos. Não há outro menu Início.

Os cards do administrador são compactos, com mesa/modalidade, número, responsável, resumo dos itens, total, status e pagamento. Clique para abrir uma janela maior com todos os itens, observações, endereço quando aplicável e ações já disponíveis para o perfil. Os avisos e as atualizações em tempo real continuam ativos. Os demais perfis mantêm suas permissões e apresentação operacional.

## Ordenação
Pedidos: aberto → pronto → em preparo → saiu para entrega → entregue. Em uma mesma etapa, os mais recentes vêm primeiro. A API mantém o limite operacional de 200 pedidos, ordenados antes de aplicar esse limite.

Dashboard: primeiro os pedidos a receber, depois os pagos. Dentro de cada grupo: pronto → em preparo → aberto → saiu para entrega → entregue. Em empate, os mais recentes primeiro. O período continua sendo o dia atual no horário de Brasília.

## Formatos brasileiros
CPF com máscara 000.000.000-00. Datas editáveis em dd/mm/aaaa, com validação de calendário. Valores monetários editáveis em 1.234,56 e exibição de totais em R$. Os valores continuam sendo enviados em formato compatível com as APIs e com o banco; não é necessário converter dados existentes. Os campos de data agora permitem digitação no formato brasileiro. CPF completo continua protegido e mascarado nas telas de consulta. Horários do histórico de caixa são apresentados em Brasília.

## Ícones dos produtos
Em Gerenciar → Produtos, escolha um dos ícones sugeridos ou digite outro no campo Ícone. A seleção só é persistida ao salvar o cadastro. Produtos com foto continuam exibindo a foto; sem foto, aparece o ícone escolhido.

Validação: 42 testes Python e testes de interação DOM para cards, janela ampliada, mudança de status, recebimento, CPF, datas válidas/inválidas, valores e seleção de ícones.

Também conferido no Chromium: cards e detalhes, larguras de 320 a 1366 pixels sem rolagem horizontal da página, seleção de ícones, campos de valores e filtros de data.
