# Módulo fiscal NFC-e — Focus NFe

Atualização para o Restaurante Manager existente: Python/Flask, SQLAlchemy, SQLite, HTML/Jinja e JavaScript. Integração desenvolvida em 30/10/2026. Não foram feitas emissões reais nem utilizado certificado de estabelecimento durante os testes.

## O que foi entregue

- Configuração fiscal por restaurante, isolada no respectivo banco.
- Menu **Gerenciar → Configuração fiscal e NFC-e**, com confirmação da senha do administrador, CSRF e bloqueio para os demais perfis.
- Razão social, CNPJ numérico ou alfanumérico com validação dos dígitos verificadores, IE, IM, CRT, UF e ambiente.
- Token de emissão e Token Master criptografados; edição nunca devolve esses valores ao navegador.
- Certificado A1 PFX/P12 e senha criptografados, validação do arquivo e validade. Envio explícito para a empresa da Focus, com conferência do CNPJ. A validação ICP-Brasil e da titularidade ocorre no provedor.
- Série e sequência local separadas por CNPJ/ambiente/série, com reserva atômica.
- Tributação vinculada ao nome exato do item gravado na comanda.
- Geração do JSON com itens, quantidades, preços finais, impostos configurados e pagamento.
- Emissão automática opcional ao registrar pagamento no caixa, inclusive pagamentos registrados pelo acerto do entregador.
- Emissão manual de pedido já pago, pela área fiscal, para contas encerradas antes de habilitar a automação.
- Status, chave, mensagem da SEFAZ, link da DANFC-e e do XML; até 20 registros por página.
- Outbox persistente e worker próprio. Uma indisponibilidade HTTP da API não impede registrar o pagamento.

O adaptador é específico da **Focus NFe v2**. APIs de outros fornecedores exigem outro adaptador e outros payloads; não são intercambiáveis apenas trocando a URL/token.

## Instalação em um sistema existente

1. Faça backup da pasta `instance` completa, inclusive bancos, chaves e fotos. Pare a aplicação e os processadores para copiar os arquivos.
2. Copie os arquivos desta atualização para a raiz existente. **Preserve sua pasta `instance`, `.venv`, configurações de hospedagem e variáveis de ambiente.** O pacote não contém esses dados.
3. No terminal, na raiz do projeto e com o ambiente virtual correto:

```bash
python -m pip install -r requirements.txt
python fiscal_cli.py migrar
```

A migração é aditiva: cria somente quatro tabelas novas e faz backup SQLite antes de alterar cada base. Não chama `init_db.py`, não recria usuários e não apaga pedidos. É idempotente. O comando percorre restaurantes cadastrados e o banco original quando existente; para selecionar um restaurante:

```bash
python fiscal_cli.py migrar --restaurante IDENTIFICADOR_DO_LINK
```

Exemplo: no link `/r/pizzaria-do-centro/`, use `--restaurante pizzaria-do-centro`. Não é telefone, número de mesa ou ID do usuário.

4. Reinicie o aplicativo WSGI/servidor e abra a área fiscal pelo menu Gerenciar.
5. Mantenha o processador ativo em processo separado:

```bash
python fiscal_cli.py processar --continuo
```

Para executar uma rodada, sem manter o processo aberto:

```bash
python fiscal_cli.py processar
```

Pode selecionar `--restaurante IDENTIFICADOR_DO_LINK` também no processamento. Em PythonAnywhere, use uma tarefa **Always-on** para o comando contínuo; um console aberto não substitui a supervisão do processo. Em VPS, use systemd/Supervisor. Sem worker, pagamentos continuam funcionando e as notas permanecem na fila.

## Primeira configuração

1. Cadastre a empresa na Focus, configure seu endereço, habilite NFC-e e obtenha os tokens Master e de homologação.
2. Preencha os mesmos dados da empresa e o ID dela na API. O campo “Chave administrativa” é o **Token Master**, e não a senha do certificado nem uma senha adicional do Basic Auth.
3. Selecione **Teste / Homologação**. Informe série e próximo número confirmados para esse ambiente.
4. Clique **Testar conexão com a API**. O servidor consulta a empresa usando Master, confere CNPJ/token do ambiente e faz uma consulta de referência inexistente com o token de emissão. O teste não emite nem altera documentos e não grava credenciais no banco. Só um 404 JSON documentado da referência, após a conferência da empresa, é aceito como autenticação válida.
5. Salve em até dez minutos. Alterar CNPJ, ambiente, ID ou tokens invalida o teste. Campos de token vazios preservam o valor salvo somente quando compatível com o emitente/ambiente.
6. Para certificado local, escolha PFX/P12, informe a senha e salve. Recarregue a página e use **Enviar certificado salvo à Focus**. O envio altera o certificado da empresa do provedor e pode afetar as emissões de produção do mesmo CNPJ; por isso é uma ação separada do teste de conexão.
7. Configure **Tributação dos itens** com o responsável fiscal. Não foram preenchidos NCM/CFOP/CST reais para o seu restaurante.
8. Faça uma compra de teste, registre seu pagamento e acompanhe a área Emissões.

Salvar nome, IE, IM e CRT nesta tela guarda os dados locais usados na integração; não recadastra a empresa automaticamente na Focus. Mantenha esses campos iguais ao cadastro do provedor. Endereço do emitente, CSC e credenciamento permanecem configurados no painel Focus/SEFAZ.

**A alíquota padrão é de ICMS CST 00.** Não é o percentual global de todos os tributos, nem a alíquota do DAS. Ela é usada somente se o item não tiver alíquota própria.

## O fluxo do fechamento

1. `/api/pedidos/<id>/pagar` executa a operação de caixa já existente.
2. Se a emissão automática estiver habilitada, `enqueue()` adiciona uma nota pendente na **mesma transação** do pagamento, guardando os itens, valores e regras fiscais daquela venda. Nenhuma chamada HTTP é feita nessa transação.
3. O worker verifica a tributação, reserva série/número e persiste o payload criptografado e a referência **antes** do POST.
4. A requisição usa `POST /v2/nfce?ref=REFERENCIA`, com HTTP Basic: token como usuário e senha vazia. O endereço é fixo conforme o ambiente, sem aceitar URL arbitrária ou redirects.
5. A resposta é classificada e salva. A emissão de NFC-e da Focus é normalmente síncrona; o status local “Processando / conciliação” cobre respostas em processamento e situações de resultado incerto.
6. Após timeout ou queda do processo, as próximas operações são consultas `GET /v2/nfce/REFERENCIA`. Não há reenvio automático de POST e não é criada outra referência.

Há uma nota por pedido/ambiente e referência aleatória única. Cada worker usa uma trava com prazo para evitar duas emissões simultâneas do mesmo registro. A numeração não é reutilizada após um envio, inclusive se houver rejeição.

**Este módulo assume fechamento financeiro pelo pagamento integral**, como o sistema atual. Pedidos pagos antes da entrega podem emitir ao receber. Pagamento parcial, estorno, reabertura de conta paga ou emissão antes do recebimento exigem um fluxo fiscal adicional.

## Tele-entrega e destinatário

O cadastro atual do cliente não possui todos os campos fiscais de endereço. O pedido de tele-entrega entra na fila, mas não é enviado enquanto faltar o destinatário completo.

Na área Emissões, abra **Completar destinatário de tele-entrega antes do envio**. Informe o ID local da nota mostrado no card, CPF, nome, logradouro, número, bairro, município, UF e CEP. Os dados ficam criptografados. Depois use **Preparar com os dados corrigidos** se a nota estiver com erro de configuração. A versão atende vendas dentro da UF do estabelecimento; não presume que uma entrega interestadual seja NFC-e válida.

A taxa de entrega é rateada em centavos proporcionalmente ao valor dos itens, com ajuste do resíduo no último item. A base de cálculo dos perfis implementados inclui o frete. Não se cria um “produto taxa de entrega” fictício. Esse tratamento precisa corresponder à operação validada pelo contador.

## Tributação implementada e limites

Esta integração não substitui um motor fiscal completo ou o enquadramento tributário do estabelecimento.

| Área | Implementado |
| --- | --- |
| CRT 1 | CSOSN 102 e 500, sem cálculo novo de ST/FCP |
| CRT 3 | CST ICMS 00, 40, 41 e 60; CST 00 calcula base integral e alíquota configurada |
| PIS / COFINS | CST 01/02 com base integral e alíquota; CST 04–09 sem destaque |
| CFOP | Venda interna, código iniciado em 5 |
| NCM / CEST | Campos por item, com validação de formato; não consulta classificação fiscal |
| Pagamentos | Dinheiro, crédito, débito e Pix estático/dinâmico; operação sem integração TEF |
| Frete | Rateio proporcional, acrescido à base dos perfis implementados |
| Destinatário | CPF e endereço fiscal, informados pelo administrador antes do envio |

CRT 2/4 ficam disponíveis no cadastro, mas bloqueiam emissão nesta versão. Reduções de base, ICMS excluído da base PIS/COFINS, FCP, créditos, monofásicos especiais, apuração de ST retida/efetiva, IBS/CBS/IS, pagamentos mistos/TEF, retenções, códigos de benefício e particularidades de UF **não estão implementados**. Não envie uma operação que dependa desses campos usando outro CST para “passar”. Ela exige extensão do adaptador e testes fiscais específicos.

O projeto não relaciona `Item` a `Produto.id`; o item preserva nome/preço da venda. Por isso a regra é associada ao **nome exato do item**, sem adivinhar NCM pela categoria. Produtos de mesmo nome precisam compartilhar a mesma regra; se tiverem tratamentos distintos, diferencie seus nomes ou estenda o modelo com um identificador fiscal estável. Ao renomear um produto, cadastre a nova regra. Notas já preparadas preservam os dados originais.

## Produção

Produção está bloqueada por padrão no servidor, além da confirmação na interface. Só habilite após validar com o contador os perfis da empresa, a legislação/NT vigente e o resultado das notas de homologação:

```bash
FISCAL_PRODUCTION_ENABLED=1
```

No PythonAnywhere, configure essa variável **antes de importar `app` no WSGI** e no ambiente do worker. Reinicie os dois processos. Apenas trocar a seleção da tela para Produção não libera emissões.

O emitente precisa de IE ativa, credenciamento NFC-e na UF, certificado A1 e CSC configurados no provedor. O teste de token não comprova essas habilitações, a autorização SEFAZ ou a correção tributária. IBS/CBS e suas regras de transição precisam ser avaliados para o regime e a data de operação; este pacote não declara conformidade universal com a reforma tributária.

Use uma série dedicada a esta aplicação. A reserva local não coordena numeração com outro PDV ou com emissão manual no painel Focus. Não diminua o próximo número; saltos e inutilizações precisam ser conciliados pelo responsável fiscal. Ao trocar série/ambiente, confira a sequência correspondente antes de salvar.

## Rejeições, indisponibilidade e arquivos

- **Erro de configuração, sem envio:** corrija regras/credenciais/destinatário e use “Preparar com os dados corrigidos”. Valores e quantidades originais são mantidos.
- **Rejeitada pela SEFAZ:** mensagem e código são preservados. Este pacote não implementa edição/reenvio de nota rejeitada; a correção deve ser conciliada com o provedor antes de ampliar esse fluxo.
- **Timeout, HTTP inesperado ou referência não localizada:** a nota fica em processamento/conciliação. Consulte a mesma referência. A interface não oferece um botão para forçar outra emissão e correr o risco de duplicar a nota. Recuperação/reenvio de uma requisição comprovadamente não recebida precisa ser feita com a Focus e com controle da referência original.
- **Autorizada:** mostra chave e links retornados pelo provedor. A DANFC-e da API pode ser **HTML**, não PDF. O módulo guarda o link real; não inventa um endereço `.pdf`. Use imprimir/salvar em PDF no navegador quando necessário.
- Links de XML e DANFC-e são guardados, mas os arquivos não são arquivados automaticamente fora do provedor. Implemente a rotina de guarda fiscal/backup dos XMLs antes de depender deste módulo em produção.
- Cancelamento, inutilização, contingência offline e eventos fiscais não estão neste escopo. PWA não permite emitir sem internet.

## Estrutura e endpoints

| Arquivo | Responsabilidade |
| --- | --- |
| `fiscal_models.py` | Configuração, regras por item, sequência e documentos |
| `sql/001_modulo_fiscal.sql` | DDL SQLite equivalente; prefira a migração Python para backup |
| `fiscal.py` | Painel, autorização, teste, configuração, certificado e operações |
| `fiscal_provider.py` | Transporte HTTPS/Basic e interpretação segura de links |
| `fiscal_service.py` | Snapshot, tributação dos perfis, outbox, emissão e conciliação |
| `fiscal_cli.py` | Migração e worker multi-restaurante |
| `templates/fiscal.html` | Tela administrativa |
| `static/css/fiscal.css` | Layout responsivo |
| `static/js/fiscal.js` | Teste, configuração e formulários sem expor segredos |
| `tests/test_fiscal.py` | Testes com API simulada e SQLite temporário |

Alterações de integração: `app.py` registra o blueprint e enfileira no pagamento; `couriers.py` enfileira no acerto; `management_access.py` protege `/fiscal`; `base.html` inclui o menu; `config.py` adiciona a habilitação de produção. Não houve migração de coluna nas tabelas antigas.

| Método e rota relativa ao restaurante | Operação |
| --- | --- |
| `GET /fiscal` | Configuração e emissões |
| `POST /fiscal/testar` | Testar as credenciais recebidas sem salvar |
| `POST /fiscal/configurar` | Salvar após teste válido |
| `POST /fiscal/certificado/enviar` | Enviar o certificado salvo à Focus |
| `POST /fiscal/regras` | JSON `{nome_item, campos}` |
| `POST /fiscal/pedidos/<id>/emitir` | Enfileirar pedido já pago, de forma idempotente |
| `POST /fiscal/notas/<id>/consultar` | Agendar consulta da referência já enviada |
| `POST /fiscal/notas/<id>/corrigir` | Atualizar configuração de nota ainda não enviada |
| `POST /fiscal/notas/<id>/destinatario` | Completar CPF/endereço antes do envio |

Todas as rotas exigem administrador e liberação vigente da área fiscal. POST exige o CSRF já utilizado pelo sistema, por formulário ou `X-CSRF-Token`. Os caminhos recebem o prefixo `/r/IDENTIFICADOR/` automaticamente no SaaS.

## Segurança e cópias de recuperação

Tokens, certificado, senha, destinatário e payload enviado são cifrados com Fernet. A chave é criada como arquivo privado `fiscal-data.key` na pasta de dados de cada restaurante; não fica dentro do código nem em `static`. O banco possui apenas os valores cifrados desses campos. CNPJ, razão social e dados de auditoria permanecem no banco administrativo.

Faça backup **do banco e de `fiscal-data.key`**, em armazenamento protegido. Se a chave desaparecer, o módulo não cria outra por cima de credenciais existentes: é preciso restaurar a original. Perder a chave impede recuperar credenciais/certificado. Use HTTPS, permissões do usuário do servidor e backups consistentes. A criptografia no banco não protege contra comprometimento do servidor com acesso à chave.

O certificado é guardado localmente de forma cifrada e enviado à Focus só quando solicitado; o arquivo original não é publicado. Tokens não aparecem em HTML, mensagens de erro de transporte ou logs do worker. O adaptador limita a resposta HTTP, recusa redirects e usa apenas domínios fixos Focus.

## Validação executada

- Suíte existente + 14 testes fiscais iniciais: **113 testes aprovados**.
- Testes fiscais finais: **18 aprovados**, incluindo PFX sintético, SQL idempotente, bloqueio de produção e CNPJ numérico/alfanumérico.
- Navegador: configuração, teste de conexão simulado, edição da tributação, campos de token vazios e telas de 320, 390, 1024 e 1440 px sem rolagem horizontal.
- Não houve chamada fiscal autenticada à Focus, transmissão SEFAZ, validação com certificado ICP-Brasil real ou confirmação de autorização de um estabelecimento.

Para repetir os testes:

```bash
python -m unittest discover -s tests -p test_fiscal.py -v
```

## Documentação oficial consultada

- https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj
- https://doc.focusnfe.com.br/reference/autenticacao
- https://doc.focusnfe.com.br/reference/ambiente
- https://doc.focusnfe.com.br/reference/emitir_nfce
- https://doc.focusnfe.com.br/reference/consultar_empresa_por_id
- https://doc.focusnfe.com.br/reference/listar_empresas
- https://doc.focusnfe.com.br/reference/atualizar_empresa
- https://doc.focusnfe.com.br/docs/nfce-requisitos-de-credenciamento
- https://doc.focusnfe.com.br/docs/ibs-e-cbs
- https://campos.focusnfe.com.br/nfe/FormaPagamentoXML.html
