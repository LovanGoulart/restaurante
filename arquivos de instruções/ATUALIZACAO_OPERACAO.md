# Atualização de operação e notificações

## Instalar em uma instalação existente
1. Pare o servidor e o worker push. Faça backup completo da pasta instance.
2. Copie os arquivos deste pacote para a pasta do sistema, mantendo sua pasta instance atual.
3. Reinicie a aplicação e o worker. No PythonAnywhere, clique em Reload na aba Web e reinicie o processo separado do push, se utilizado.
4. Reabra o PWA ou atualize a página para carregar a versão nova dos scripts e estilos.

Não é necessário recriar ou migrar o banco. Não execute init_db.py para aplicar esta atualização. O ZIP contém o código completo e não inclui banco, chaves privadas, ambiente virtual ou histórico Git. A pasta instance existente contém também as fotos, a personalização e as chaves que devem ser preservadas.

## Ajustes
- Botão Sair disponível no cabeçalho do desktop para os cinco perfis, com encerramento da sessão pelo POST protegido por CSRF. O menu do celular foi preservado.
- Pedidos prontos do cliente e detalhes dos pedidos prontos usam fundo padrão, com faixa superior verde e cabeçalho suavemente destacado. Os cards compactos prontos da equipe mantêm sua apresentação anterior.
- Pedidos entregues e pagos têm faixa superior verde e corpo padrão, tanto no resumo quanto nos detalhes e nas entregas.
- Cozinha e garçom: pedidos em preparo com fundo azul claro.
- Cozinha: ao concluir o preparo, a janela fecha e o pedido sai da fila, sem mensagem de indisponibilidade.
- Garçom: pedidos entregues e pagos são posicionados no final. A ordem dos demais status e a restrição aos pedidos do salão permanecem.
- Detalhes do administrador no desktop sem rolagem interna. Para pedidos maiores que a altura da tela, use a rolagem da página; todos os itens e ações permanecem acessíveis.
- Notificações da central e Web Push carregam o número do pedido no link. Administração, garçom e cozinha abrem os detalhes; o cliente e o entregador são levados ao card correspondente. A consulta individual é autorizada no servidor, mesmo quando o pedido está fora dos 200 registros da lista ou é uma entrega antiga. A cozinha pode consultar o pedido apontado pela notificação, mas sua fila continua somente com abertos e em preparo.
- Confirmação de entrega e acerto: o botão só é habilitado ao marcar a caixa existente. A exigência de confirmação no servidor também foi mantida.
- A seleção de entregas para acerto é preservada nas atualizações automáticas; a confirmação em andamento não é substituída por uma atualização de fundo.
- Botões manuais Atualizar ocultos. SSE e consultas periódicas de recuperação continuam ativos.

## Verificação
47 testes automatizados aprovados, incluindo permissões do detalhe, ordenação, entrega antiga por notificação, confirmação obrigatória e logout dos cinco perfis. Conferência em Chromium das cores, preparação na cozinha, abertura por notificação, controles de confirmação, saída das contas e detalhes com 35 itens. Larguras de 320, 390, 850 e 1366 pixels verificadas sem alargamento horizontal da página de pedidos.

A entrega externa real de Web Push continua dependendo da configuração do servidor, do worker, da permissão do navegador e do dispositivo. Os testes de push são simulados; o vínculo ao pedido e a navegação foram verificados localmente.
