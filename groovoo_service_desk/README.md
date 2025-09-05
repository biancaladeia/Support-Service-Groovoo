# Groovoo Service Desk (MVP)

Esta aplicação é um MVP de *Service Desk* para uso interno em empresas de
venda de tickets como a Groovoo.  Foi desenvolvida do zero em Python
utilizando o micro‐framework Flask e bibliotecas auxiliares para
autenticação e banco de dados.  O foco é fornecer uma interface simples e
funcional para gerenciamento de chamados de suporte.

## Funcionalidades

- **Autenticação de usuários**: atendentes podem criar uma conta e fazer
  login.  As rotas são protegidas para garantir que apenas usuários
  autenticados acessem as funcionalidades.
- **Gestão de tickets**: cada ticket possui um ID automático, nome e
  contato do cliente, canal de atendimento, categoria, descrição, status
  (Aberto, Aguardando, Fechado), data/hora de criação, atendente
  responsável e lista de comentários e anexos.
- **Anexos**: é possível anexar imagens (PNG/JPG/GIF) ou PDFs aos tickets.
- **Dashboard**: a tela inicial exibe contadores de tickets por status,
  filtros por categoria e busca livre, além de uma lista de tickets em
  formato de cartões.
- **Detalhes do ticket**: ao abrir um ticket é possível ver todos os
  campos, anexos e comentários.  Também é possível adicionar novos
  comentários, anexar novos arquivos e alterar o status.
- **Exportação**: tickets com status **Aberto** podem ser exportados para
  CSV ou Markdown através de um clique.
- **Visual**: o tema escuro com tons de roxo segue a identidade da Groovoo
  conforme o estilo utilizado no site oficial【954577895250465†L0-L12】.

## Instalação e execução

1. Crie um ambiente virtual e instale as dependências listadas em
   `requirements.txt`:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Defina a variável de ambiente `FLASK_APP` apontando para o módulo
   principal e execute o servidor de desenvolvimento:

   ```bash
   export FLASK_APP=groovoo_service_desk/app.py
   flask run
   ```

   O aplicativo criará automaticamente o arquivo de banco de dados
   `service_desk.db` na primeira execução.

3. Acesse `http://localhost:5000` no seu navegador, crie uma conta e
   comece a registrar tickets.

## Organização do código

- `app.py` – arquivo principal com inicialização do Flask, modelos, rotas
  e helpers.
- `config.py` – configurações de segredo, banco de dados e uploads.
- `templates/` – páginas HTML com Jinja2 (base, login, cadastro,
  dashboard, criação de tickets, detalhes e páginas de erro).
- `static/css/style.css` – folha de estilos baseada no rascunho da Groovoo
  com paleta de cores roxa e lavanda【954577895250465†L0-L12】.
- `static/uploads/` – pasta onde são salvos os anexos enviados pelos
  usuários (vazia inicialmente; será criada em tempo de execução).

## Observações

- Esta é uma versão mínima e ilustrativa.  Em um ambiente de produção
  recomenda‑se configurar um segredo aleatório e usar um banco de dados
  mais robusto que SQLite.
- A autenticação utiliza *Flask‑Login* e armazena senhas de forma segura
  com hashes.
- Para categorias e canais específicos de atendimento convém substituir
  os campos de texto por listas pré‑definidas conforme as regras de
  negócio.