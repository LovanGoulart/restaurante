# Nome e mesa no pedido pelo QR Code

O cliente agora informa nome e número da mesa na entrada do salão. Os dois campos são obrigatórios e validados no servidor. O pedido é gravado com essa mesa, que aparece nos cards, detalhes e mensagens de notificação. A comanda continua sendo definida pelo garçom, com a mesa já preenchida para conferência.

Na versão deste projeto, a tela da rota `/salao` fica no arquivo `templates/qr_entrada.html`.

## Aplicar sobre a última versão enviada

Substitua somente estes cinco arquivos, preservando a estrutura de pastas:

- `salon_qr.py`
- `notifications.py`
- `templates/qr_entrada.html`
- `templates/pdv.html`
- `static/js/app.js`

Não é necessário migrar ou recriar o banco: a atualização usa o campo `numero_mesa` já existente. Preserve `instance`, bancos, chaves, fotos e suas configurações.

Reinicie a aplicação e o worker; no PythonAnywhere, use Reload. Atualize a página no navegador para carregar o JavaScript novo.

Sessões antigas sem mesa serão encaminhadas ao formulário antes de fazer novos pedidos, preservando o usuário e seu histórico. Pedidos anteriores continuam com os dados que já estavam gravados; sua mesa não é presumida automaticamente.

No cardápio, o cliente verá sua mesa e poderá corrigir nome/mesa para os próximos pedidos. Essa correção não muda a mesa de pedidos já enviados.

O garçom recebe a mesa preenchida ao abrir o pedido e completa o atendimento com a comanda. Ele poderá conferir/corrigir a mesa antes de vincular; o bloqueio de uma comanda aberta em outra mesa continua ativo.
