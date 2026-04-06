# RDO Digital — Diário de Obra por Voz e Painel Web

Sistema de registro de Relatório Diário de Obra (RDO) com backend FastAPI, painel web em React e integrações por mensagem. O projeto já possui fluxo web funcional para dashboard, diário da obra, workflow de aprovação e exportação HTML/PDF.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Backend | FastAPI (Python 3.13) |
| Frontend | React + Vite + TypeScript |
| Banco | PostgreSQL + SQLAlchemy |
| LLM (intent) | Ollama — `qwen2.5:7b-instruct` |
| Transcrição | OpenAI Whisper API (`whisper-1`) |
| Telegram | Bot API oficial |
| WhatsApp | Evolution API (stub) |
| PDF | WeasyPrint + Jinja2 |

---

## Estrutura do projeto

```
rdo-obra/
├── app/
│   ├── adapters/
│   │   ├── base.py               # Interface BaseAdapter
│   │   ├── telegram.py           # Adapter Telegram Bot API
│   │   └── whatsapp.py           # Adapter Evolution API (stub)
│   ├── core/
│   │   ├── config.py             # Settings via pydantic-settings + .env
│   │   ├── orchestrator.py       # Ponto central: msg → classifica → registra
│   │   ├── relations.py          # Relation Engine: impactos cruzados
│   │   └── types.py              # IncomingMessage, OutgoingMessage, enums
│   ├── routes/
│   │   ├── atividades.py
│   │   ├── efetivo.py
│   │   ├── materiais.py
│   │   ├── equipamentos.py
│   │   ├── clima.py
│   │   ├── anotacoes.py
│   │   ├── fotos.py
│   │   ├── obras.py
│   │   ├── empresas.py
│   │   ├── usuarios.py
│   │   ├── rdo.py                # Geração de RDO (JSON + HTML preview)
│   │   ├── telegram_webhook.py
│   │   └── whatsapp_webhook.py
│   ├── services/
│   │   ├── intent.py             # Classificação via Ollama
│   │   ├── transcription.py      # Whisper API
│   │   └── pdf.py                # Geração de PDF
│   ├── models.py                 # SQLAlchemy models (12 tabelas)
│   ├── database.py               # Engine + SessionLocal + init_db()
│   ├── main.py                   # Entry point FastAPI
│   └── seed.py                   # Dados de teste
├── docs/
│   ├── ARCHITECTURE.md
│   └── ISSUES.md
├── templates/
│   └── rdo_default.html          # Template HTML para PDF
├── .env.example                  # Template de configuração
└── requirements.txt
```

---

## Banco de dados — 12 tabelas

```
empresas
  └── obras
        ├── usuarios               # identificados por telefone/chat_id
        ├── atividades             # INICIADA → EM_ANDAMENTO → CONCLUIDA
        │     └── atividade_historico
        ├── efetivo
        ├── anotacoes              # manuais + geradas pelo Relation Engine
        ├── materiais
        ├── equipamentos
        ├── clima
        │     └── dias_improdutivos
        └── fotos
```

---

## Fluxo de uma mensagem

```
[Telegram/WhatsApp] → adapter.parse_incoming()
    → IncomingMessage (canal, telefone, tipo, texto, audio_path)
    → Orchestrator.processar()
        → identifica usuário pelo telefone/chat_id
        → se áudio: transcription.transcribe_audio() → texto
        → intent.classify_intent() via Ollama → {intent, confidence, data}
        → se confidence < 0.6: pede reformulação
        → registra no módulo correto
        → RelationEngine verifica impactos cruzados
        → OutgoingMessage → adapter.send_message()
```

---

## Setup

### Pré-requisitos

- Python 3.13+
- PostgreSQL
- [Ollama](https://ollama.ai) com `qwen2.5:7b-instruct` rodando localmente
- Conta OpenAI (para Whisper)
- Bot do Telegram criado via [@BotFather](https://t.me/botfather)

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# editar .env com suas chaves
```

### 2. Banco de dados

```bash
sudo pg_ctlcluster <versao> main start
sudo -u postgres psql -c "CREATE USER rdo WITH PASSWORD 'rdo';"
sudo -u postgres psql -c "CREATE DATABASE rdo_digital OWNER rdo;"
```

### 3. Instalar dependências

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Seed + API

```bash
venv/bin/python -m scripts.seed_demo
uvicorn app.main:app --reload --port 8000
```

Swagger em `http://localhost:8000/docs`

Para popular massa retroativa com mais controle, veja [RETRO_SEED_GUIDE.md](/home/lexkaliking/.openclaw/workspace/rdo-obra/docs/RETRO_SEED_GUIDE.md).

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

App web em `http://localhost:5173`

### 6. Registrar webhook do Telegram (ngrok)

```bash
ngrok http 8000
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d '{"url": "https://<ngrok_url>/telegram/webhook"}'
```

---

## Status do MVP

| Módulo | Status |
|---|---|
| Models + banco PostgreSQL | Implementado |
| Seed com dados retroativos e fotos fake | Implementado |
| Intent classifier (Ollama) | Implementado |
| Transcription (Whisper API) | Implementado |
| Orchestrator | Implementado |
| Relation Engine | Implementado |
| Adapter Telegram | Implementado |
| CRUD routes (todas as entidades) | Implementado |
| Geração RDO (HTML preview + PDF) | Implementado |
| Adapter WhatsApp (Evolution API) | Stub — não funcional |
| Dashboard web | Implementado |
| Autenticação (JWT/token) | Implementado |
| Testes automatizados | Implementado parcialmente |
| Deploy (Docker + VPS) | Não implementado |

Ver `docs/ISSUES.md` para pendências técnicas detalhadas.

Para uma leitura técnica orientada a produto (em linguagem acessível), veja `docs/REVISAO_COMPLETA_MVP.md`.

---

## Contribuindo

Este é um projeto em desenvolvimento ativo. Para reportar bugs ou sugerir melhorias, abra uma issue.
