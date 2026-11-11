# Atualização — Programa de fidelidade

Implementação baseada no arquivo restaurante(1).zip enviado. Este pacote contém somente arquivos novos/alterados e este guia. Não contém bancos de dados, pastas instance, fotos, credenciais ou configurações de produção.

## Instalação sem substituir seus registros

1. Pare o sistema (Ctrl+C no terminal que executa o servidor; em hospedagem, suspenda os processos durante a migração).
2. Faça uma cópia de segurança da pasta atual do sistema.
3. Copie o CONTEÚDO da pasta restaurante deste pacote para sua pasta restaurante existente, mesclando static/templates e substituindo apenas os arquivos de mesmo nome. Não apague nenhuma pasta.
4. No terminal, dentro da pasta onde estão app.py e migrate_loyalty.py, usando o mesmo Python/ambiente virtual do sistema, execute:

```powershell
python migrate_loyalty.py
```

5. Confira as linhas OK dos bancos utilizados pelos restaurantes. Reinicie o sistema pelo comando que já utiliza e atualize a página. No aplicativo instalado, feche e abra novamente para carregar os novos arquivos.
6. Como administrador do restaurante, abra Painel de Controle → Fidelidade, habilite o programa, informe a regra e cadastre as recompensas.

Não execute init_db.py e não substitua seus arquivos restaurante.db.

A migração procura instance/restaurante.db e instance/plataforma/restaurantes/*/restaurante.db. Antes de adicionar tabelas, cria ao lado de cada banco compatível um backup restaurante-antes-fidelidade-DATA-HORA.db. Não altera tabelas antigas nem reaplica a criação quando as quatro tabelas já existem. Bancos antigos incompatíveis encontrados na busca automática recebem IGNORADO e permanecem intactos. O ZIP enviado contém um banco antigo desse tipo além dos três bancos compatíveis.

Para um caminho personalizado, use:

```powershell
python migrate_loyalty.py --banco "C:\caminho\restaurante.db"
```

Se DATABASE_URL estiver definida, a migração usa o SQLite indicado nela. O programa foi integrado ao SQLite utilizado neste projeto. Se aparecer ERRO em um banco utilizado pelo sistema, não inicie o servidor antes de resolver o erro. Não restaure um backup antigo sobre pedidos novos: backups são para recuperação controlada, com o servidor parado.

## Regras implementadas

- Programa inicialmente desabilitado e configurado separadamente por restaurante.
- Apenas pedidos criados pelo próprio cliente autenticado, em retirada ou entrega, participam. Pedidos de caixa, garçom e QR Code não pontuam.
- Base: subtotal dos produtos, incluindo as opções já incorporadas ao preço pelo sistema, SEM taxa de entrega.
- Blocos completos por pedido. Exemplo: R$ 20 = 3 pontos; R$ 39,90 = 3; R$ 40 = 6. O restante não é acumulado para outra compra.
- Crédito somente após as duas condições: pagamento confirmado e status entregue (ou retirada concluída). No delivery recebido pelo entregador, o pagamento é confirmado no acerto, conforme o fluxo existente.
- Regra e pontuação prevista ficam registradas na criação do pedido. Alterar a regra não recalcula compras anteriores. Uma compra elegível já registrada ainda recebe seus pontos ao ser concluída, mesmo que o programa seja desativado depois.
- Pedidos antigos, anteriores à instalação, não geram pontos retroativos.
- Saldo e histórico individuais; validação no servidor e proteção contra pedidos repetidos ou resgates simultâneos.
- Histórico registra ganhos, resgates e estornos, com data e pedido. A tela mostra as últimas 100 movimentações; o saldo considera todas.
- Ao desabilitar: menus ocultos, página/API/resgate bloqueados, saldo e histórico preservados.

## Resgate

- Uma unidade de uma recompensa por pedido de resgate, separado de compras pagas.
- Administrador escolhe um produto existente, custo em pontos e descrição da apresentação incluída. Pode editar ou excluir da lista; a exclusão preserva o histórico.
- Produtos inativos/excluídos no cadastro não podem ser resgatados.
- Para pizza ou outro produto configurável, descreva a versão exata oferecida (tamanho, sabor, massa etc.). O resgate não abre o personalizador e não acrescenta cobranças ao produto.
- Na retirada: total R$ 0,00, identificado como pago com pontos, sem lançamento fictício no caixa.
- Na entrega: cobra somente a taxa fixa que já está configurada no restaurante. O projeto enviado usa essa taxa; não foi criado outro cálculo por bairro.
- Pontos são debitados na mesma transação que confirma e grava o pedido. Erros de validação não debitam; reenviar a mesma tentativa não gera novo débito.
- Resgates não geram novos pontos, inclusive sobre a taxa de entrega.
- Em Painel de Controle → Fidelidade → Resgates recentes, o administrador pode cancelar e devolver os pontos antes do preparo, desde que não haja entrega atribuída nem taxa já recebida. O estorno acontece uma única vez. Após início do preparo, esse cancelamento é bloqueado para não interferir na cozinha/caixa.

## Teste manual, etapa por etapa

Use preferencialmente uma cópia de teste de sua instalação; pedidos de teste no sistema real entram na operação normal.

1. **Configuração:** habilite R$ 20,00 = 3 pontos. Adicione uma recompensa por 3 pontos. Edite sua descrição/custo, exclua da lista e cadastre novamente. Verifique a lista atualizada.
2. **Menus:** com cliente cadastrado, abra Fidelidade na navegação desktop e no Ver Mais mobile. Administrador configura pelo Painel de Controle. Garçom, cozinha e visitante QR Code não devem ter acesso à página do cliente.
3. **Acúmulo:** faça uma compra online de R$ 40,00 em produtos. Antes do pagamento e conclusão, saldo não muda. Confirme pagamento e retirada/entrega: entram 6 pontos. Recarregue as telas e repita consultas: não duplica.
4. **Taxa:** repita como delivery. R$ 40 em produtos + taxa de entrega continua gerando 6 pontos, não pontos sobre a taxa. Se recebeu com o entregador, confirme o acerto no caixa aberto.
5. **Resgate retirada:** escolha a recompensa e retirada. Total deve ser zero; confirme. Produto aparece no fluxo normal de pedidos/cozinha e saldo diminui 3 pontos. Consulte o histórico.
6. **Resgate entrega:** acumule saldo novamente e resgate com entrega. Informe o endereço; total deve ser somente a taxa. Conclua entrega e pagamento pelo fluxo existente. O resgate não gera novos pontos.
7. **Saldo insuficiente:** com saldo menor que o custo, o botão não deve permitir resgate; abrir diretamente o endereço do resgate também será recusado.
8. **Isolamento:** entre com outro cliente. Ele deve ver somente o próprio saldo/histórico e não poder usar os pontos do primeiro.
9. **Estorno:** resgate e, antes do preparo, cancele pela área administrativa da fidelidade. O pedido fica cancelado, saldo volta e aparece o estorno. Repetir não devolve pontos novamente. Iniciar o preparo bloqueia esse cancelamento.
10. **Mudança de regra:** crie uma compra sob a regra antiga, altere a configuração e conclua aquela compra. Ela mantém a regra da criação; a próxima compra usa a nova.
11. **Desabilitar:** desative a fidelidade. Cliente deixa de ver o menu e acesso direto retorna bloqueado. Reative: saldo anterior reaparece.
12. **Demais operações:** confira pedidos normais, PDV, cozinha, caixa e delivery, para validar a instalação no seu ambiente.

## Arquivos incluídos

Novos:
- loyalty_models.py — quatro tabelas novas.
- loyalty.py — configuração, saldo, histórico, resgate e estorno.
- migrate_loyalty.py — migração aditiva e backups.
- templates/fidelidade.html, fidelidade_admin.html, fidelidade_resgate.html e _fidelidade_historico.html.
- static/css/loyalty.css e static/js/loyalty.js.

Alterados:
- app.py — registro do módulo e bloqueio de pagamento de pedido cancelado.
- customers.py — integração ao checkout online existente.
- notifications.py — crédito na transação de pagamento/conclusão e evento de cancelamento.
- management_access.py — proteção da área administrativa de fidelidade.
- orders_service.py — impede preparo de resgate cancelado.
- templates/base.html e templates/pedidos.html — acesso à fidelidade.
- static/js/app.js — rótulos de pontos/cancelamento e ações compatíveis.
- static/sw.js — atualização do cache do aplicativo.

Tabelas criadas: fidelidade_config, fidelidade_recompensa, fidelidade_pedido, fidelidade_movimento. Nenhuma tabela antiga é substituída.

## Validação realizada

12 testes automatizados específicos passaram: crédito único, regra histórica, arredondamento, resgate gratuito, taxa de entrega, saldo insuficiente, acesso/CSRF, isolamento entre clientes, concorrência, estorno, configuração, renderização do checkout e migração preservando registros. JavaScript validado quanto à sintaxe.

Migração executada em cópias dos três bancos de restaurantes do ZIP: comparação de todos os registros das tabelas antigas confirmou preservação; backups conferidos e segunda execução sem duplicar tabelas. O banco legado incompatível foi recusado sem alteração.

A suíte anterior já possui falhas no próprio ZIP original; as falhas observadas na versão alterada também estão presentes na original. Não foi feita correção de recursos sem relação com fidelidade. A interface foi validada pela renderização de templates e testes HTTP; a conferência visual em celular deve ser feita pelas etapas acima.
