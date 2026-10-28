# Atualização: identidade visual, fotos e início administrativo

1. Pare o servidor. Faça backup completo da pasta instance da instalação existente.
2. Copie os arquivos deste pacote para a pasta do projeto, preservando sua pasta instance.
3. No terminal, com o ambiente Python do projeto ativado, execute:

   python -m pip install -r requirements.txt

4. Reinicie o servidor. No PythonAnywhere, recarregue a aplicação pela aba Web.
5. Entre como administrador. A página inicial do administrador é /pedidos, chamada Pedidos.
6. Em Gerenciar (ou Mais no celular), abra Personalização e fotos.

Não há alteração nas tabelas do banco nesta atualização; não execute init_db.py em uma instalação existente. O ZIP não contém banco, chaves privadas, ambiente virtual ou histórico Git.

## Recursos
- Nome do restaurante: atualizado também na configuração Loja e exibido no menu superior.
- Cores: menu superior, cor principal dos botões, destaques e fundo. Estados operacionais mantêm suas cores semânticas. Escolha combinações legíveis.
- Capa do PDV: título, descrição e foto substituindo a ilustração; permite restaurar a ilustração.
- Fotos: upload por produto, remoção e substituição; aparecem no salão e no cardápio público. JPG/PNG/WebP até 5 MB e 20 megapixels. Imagens são convertidas para JPEG, redimensionadas e metadados removidos.
- Pedidos: cards compactos para o administrador. Clique no card para abrir os detalhes ampliados e executar as ações do pedido. A listagem operacional continua limitada aos 200 pedidos consultados pela API. Não há tela adicional de início.

Configurações visuais ficam em instance/appearance.json e imagens em instance/media. Inclua toda a pasta instance nos backups. Alterações no código não substituem esses arquivos. Fotos antigas ficam preservadas no disco ao substituir/remover sua referência.

Somente administradores podem alterar a identidade visual e as fotos ou acessar o painel inicial. Este controle abrange as configurações disponibilizadas; mudanças arbitrárias de regras e código continuam exigindo desenvolvimento.

Validação: 37 testes preexistentes aprovados e testes adicionais de identidade, permissões, upload inválido/válido, remoção, filtros e paginação. A interface deve ser conferida nos dispositivos usados na operação.
