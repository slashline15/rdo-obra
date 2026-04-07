# RDO Digital

Plataforma de Relatório Diário de Obra com backend em FastAPI, painel web em React e integrações por mensageria. O sistema já opera com autenticação, níveis de acesso, convites tokenizados, workflow de aprovação do diário, trilha de auditoria e exclusão lógica com lixeira administrativa.

## Visão geral

Hoje o projeto está organizado em dois blocos principais:

- Backend `FastAPI` para autenticação, regras de negócio, auditoria, geração de RDO e integrações.
- Frontend `React + Vite + TypeScript` para operação diária, dashboard, gestão de usuários e consulta da Wiki interna.

O ciclo principal já coberto pelo produto é:

1. Usuário autenticado entra no painel.
2. Acesso é limitado por nível e por obra.
3. O diário é preenchido com efetivo, atividades, materiais, anotações, clima e fotos.
4. O diário segue para revisão, aprovação e eventual reabertura.
5. Toda mudança crítica fica registrada para rastreabilidade.

## Arquitetura atual

### Backend

- `app/main.py`: composição da API.
- `app/models.py`: modelos SQLAlchemy.
- `app/routes/`: rotas por domínio.
- `app/core/`: autenticação, permissões, configuração e orquestração.
- `app/services/`: PDF, auditoria, relation engine, transcrição e intent.
- `migrations/`: versionamento de schema com Alembic.

### Frontend

- `frontend/src/pages/`: páginas do painel.
- `frontend/src/hooks/`: consumo da API e mutações.
- `frontend/src/lib/`: autenticação, providers e utilitários.
- `frontend/src/content/wiki/`: arquivos Markdown carregados pela rota `/docs`.

## Tecnologias

| Camada | Tecnologias |
| --- | --- |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic 2 |
| Banco de dados | PostgreSQL |
| Frontend | React 19, Vite, TypeScript, TanStack Router, TanStack Query |
| PDF | WeasyPrint + Jinja2 |
| IA e processamento | Ollama, Whisper API, relation engine |
| Mensageria | Telegram Bot API, Evolution API (base/stub) |
| Testes | Pytest |

## Níveis de acesso

O sistema adota três níveis operacionais:

- **Nível 1 - Admin Geral**: visão de todas as obras, gestão de usuários, convites, auditoria e lixeira administrativa.
- **Nível 2 - Co-responsável**: atua dentro de uma obra específica, pode revisar registros e aprovar diário quando houver delegação.
- **Nível 3 - Operacional**: alimenta o diário e consulta informações da própria obra.

Além do login, toda autorização combina:

- nível do usuário;
- vínculo com `obra_id`;
- regras de delegação, como aprovação de diário.

## Segurança e governança já implementadas

- JWT para autenticação do painel.
- Convites com token, expiração e aceite ativo do usuário.
- Bootstrap legado bloqueado por token explícito de instalação.
- Escopo por obra validado nas rotas sensíveis.
- Soft delete do diário com restauração e auditoria.
- Registro de alterações para eventos críticos do fluxo do diário.

## Wiki interna

O painel já possui a rota `/docs` com a base institucional em Markdown. Ela documenta:

- visão geral do sistema;
- níveis de acesso;
- soft delete;
- fluxo do RDO;
- uso de IA;
- mapa de dados;
- convites e permissões.

Essa Wiki é a fonte única de verdade para alinhar produto, operação e arquitetura antes dos próximos módulos.

## Como rodar localmente

### 1. Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure o `.env` com pelo menos:

- `DATABASE_URL`
- `JWT_SECRET`
- credenciais de mensageria e IA, quando aplicável

### 2. Banco e migrations

```bash
alembic upgrade head
```

Se quiser dados de demonstração:

```bash
venv/bin/python -m scripts.seed_demo
```

### 3. Subir a API

```bash
uvicorn app.main:app --reload --port 8000
```

API e Swagger:

- `http://localhost:8000`
- `http://localhost:8000/docs`

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Painel web:

- `http://localhost:5173`

## Qualidade e validação

Principais comandos de verificação:

```bash
./venv/bin/pytest -q --capture=no
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

## Estado atual do produto

Já implementado:

- autenticação e sessão web;
- níveis de acesso e escopo por obra;
- gestão de convites;
- dashboard e painel por obra;
- fluxo do diário com submissão, aprovação, rejeição e reabertura;
- PDF e exportação do RDO;
- lixeira administrativa com restauração;
- helper interno em Markdown.

Em definição para o próximo ciclo:

- cronograma;
- curva S;
- financeiro;
- integrações externas estruturadas.

## Documentação complementar

- [Arquitetura técnica](docs/ARCHITECTURE.md)
- [Guia de seed retroativa](docs/RETRO_SEED_GUIDE.md)
- [Revisão técnica anterior](docs/REVISAO_COMPLETA_MVP.md)
