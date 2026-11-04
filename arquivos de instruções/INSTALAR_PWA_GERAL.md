# PWA exclusivo da administração geral

## Aplicar esta atualização

1. Pare o sistema local ou aguarde para recarregar a aplicação na hospedagem.
2. Extraia este ZIP na pasta do projeto, onde estão app.py e platform_admin.py.
3. Substitua platform_admin.py e templates/geral_base.html. Copie também a pasta static/geral-pwa inteira.
4. Reinicie o sistema. No PythonAnywhere, use Reload na aba Web.
5. No navegador, abra /geral/login no endereço do sistema e pressione Ctrl+F5.

Não execute init_db.py ou setup_geral.py para aplicar esta atualização. Nenhuma alteração no banco, nos usuários ou nos planos é necessária.

## Instalar no PC de casa

1. No Chrome ou Edge, abra o endereço hospedado seguido de /geral/login.
   Exemplo: https://restaurantes.pythonanywhere.com/geral/login
2. Entre com o e-mail e a senha do administrador geral.
3. No painel, clique em “Instalar Manager Geral” quando o navegador oferecer a instalação.
4. Confirme no diálogo do navegador. O aplicativo aparecerá como “Manager Geral”, com ícone próprio, podendo ser fixado no menu Iniciar ou na barra de tarefas.
5. Se o botão não aparecer, procure o ícone de instalação na barra de endereço ou a opção de instalar aplicativo no menu do navegador. Caso já esteja instalado, abra pelo atalho existente.

A instalação precisa de HTTPS na hospedagem. Para testes locais, localhost e 127.0.0.1 são aceitos. Use a porta que o seu servidor mostrar no terminal. O botão depende do suporte e dos critérios do navegador.

## Como funciona

- Nome: Manager Geral.
- Identidade, início e escopo próprios: /geral/.
- Ícone exclusivo, diferente do aplicativo dos restaurantes.
- Ao abrir o atalho, acessa a administração geral. Se a sessão tiver terminado, pede o login do proprietário.
- O botão de instalação aparece no painel autenticado; não é inserido nas telas dos restaurantes.
- Os PWAs dos restaurantes continuam nos próprios endereços /r/<link-do-restaurante>/, sem compartilhar o escopo com o painel geral.
- O aplicativo usa o sistema hospedado; é necessária internet. Se usar um servidor local, ele precisa estar ligado e executando.
- Sem conexão, aparece apenas um aviso genérico. O PWA geral não armazena páginas autenticadas nem dados de restaurantes ou administradores em cache.
- A instalação não elimina a senha e não concede novas permissões.

## Verificações executadas

- Manifesto e critérios de instalação reconhecidos pelo Chromium.
- Registro dos dois service workers, com escopos independentes, no mesmo domínio.
- Cache limitado ao aviso genérico offline e preservação dos caches do restaurante.
- Login, saída e proteção do painel após sair.
- Visualização em 320, 390 e 1440 px, sem rolagem horizontal.
- Testes existentes da plataforma e verificações específicas das rotas PWA.

A confirmação de instalação no Windows deve ser feita por você no navegador do seu PC.
