# ISSUES.md — Problemas Conhecidos e Pendências Técnicas

> Atualizado: 2026-04-02
> Estado: MVP em desenvolvimento. API implementada, não testada end-to-end.

---

## 🔴 Bloqueadores (impedem o teste básico)

### ISSUE-001 — PostgreSQL não sobe automaticamente no WSL2
**Descrição:** O `sudo service postgresql start` no WSL2/Kali retorna sucesso mas não sobe o cluster real. O serviço systemd é apenas um wrapper sem efeito.
**Causa:** WSL2 não roda systemd por padrão; o cluster PostgreSQL precisa ser iniciado via `pg_ctlcluster`.
**Fix necessário:**
```bash
sudo pg_ctlcluster <versao> main start
# ex: sudo pg_ctlcluster 15 main start
```
**Sugestão:** Criar script `scripts/dev-start.sh` que sobe PostgreSQL + API automaticamente no ambiente de desenvolvimento.

### ISSUE-002 — Usuário de teste não tem `telegram_chat_id` mapeado
**Descrição:** O adapter Telegram identifica usuários pelo campo `telefone` usando o `chat_id` do Telegram (inteiro). O seed popula usuários com números de telefone fictícios (formato WhatsApp), não com chat_ids reais do Telegram.
**Impacto:** Qualquer mensagem recebida pelo bot retorna "Número não cadastrado".
**Fix necessário:** Após receber a primeira mensagem no bot, pegar o `chat_id` do payload (`message.chat.id`) e atualizar o campo `telefone` do usuário de teste no banco:
```sql
UPDATE usuarios SET telefone = '<chat_id>' WHERE nome = 'Daniel Silva';
```
**Melhoria futura:** Fluxo de onboarding — usuário manda `/start` no bot e o sistema registra automaticamente o chat_id.

---

## 🟡 Problemas de implementação (quebram fluxos específicos)

### ISSUE-003 — `transcription.py` não lê configuração do `.env`
**Descrição:** O `transcription.py` usa `os.getenv()` direto, mas o `.env` só é carregado pelo `pydantic-settings` (via `config.py`) quando a aplicação inicia. Em testes isolados (scripts externos), as variáveis não são carregadas.
**Fix:** Adicionar `from dotenv import load_dotenv; load_dotenv()` no topo do módulo, ou injetar as configs via `settings` do `config.py`:
```python
from app.core.config import settings
WHISPER_API_KEY = settings.whisper_api_key or settings.openai_api_key
```

### ISSUE-004 — Rota `/telegram/webhook` instancia `TelegramAdapter` e `Orchestrator` fora do contexto de request
**Descrição:** Em `telegram_webhook.py`, `TelegramAdapter()` é instanciado no escopo do módulo (linha `adapter = TelegramAdapter()`), o que causa erro se `settings.telegram_bot_token` for `None` no momento do import.
**Fix:** Mover a instanciação para dentro da função de endpoint ou usar `Depends()`.

### ISSUE-005 — `routes/servicos.py` ainda existe com referência ao modelo antigo
**Descrição:** A refatoração renomeou `Servico` para `Atividade`, mas `app/main.py` ainda importa e registra `servicos.router`. Se `routes/servicos.py` não existir ou tiver imports quebrados, a API não sobe.
**Fix:** Verificar se `routes/servicos.py` foi atualizado para usar `Atividade` ou removê-lo e limpar o import em `main.py`.

### ISSUE-006 — `Orchestrator` usa `await` em métodos síncronos do banco
**Descrição:** Os métodos `_registrar_atividade`, `_registrar_efetivo`, etc. são síncronos (`def`, não `async def`) mas são chamados com `await` em `_registrar()`. Isso causa `TypeError: object NoneType can't be used in 'await' expression`.
**Fix:** Remover `await` nas chamadas dentro de `_registrar()` ou converter os métodos para async.

### ISSUE-007 — Relation Engine não é chamado corretamente para `atividade`
**Descrição:** `_registrar_atividade()` cria a atividade mas não chama o Relation Engine. Apenas `clima` e `material` disparam relações. Atividades iniciadas deveriam verificar dependências (`atividade_pai_id`).
**Status:** Funcionalidade não crítica para MVP, mas documentada para não ser esquecida.

---

## 🟢 Melhorias planejadas (pós-MVP)

### ISSUE-008 — Matching semântico para conclusão de atividade
**Descrição:** `_concluir_atividade()` usa matching por palavras-chave simples. Se o usuário disser "terminamos a laje" e a descrição no banco for "Execução de concretagem da laje do 2º pavimento tipo", o match pode falhar.
**Solução planejada:** pgvector + embeddings (sentence-transformers ou OpenAI) para busca semântica. Estrutura já prevista no banco (`pgvector`).

### ISSUE-009 — Adapter WhatsApp não implementado
**Descrição:** `app/adapters/whatsapp.py` existe mas é um stub sem lógica real. Evolution API requer instância self-hosted configurada.
**Pendências:**
- Instalar Evolution API (Docker)
- Implementar autenticação da instância
- Mapear formato dos webhooks da Evolution para `IncomingMessage`
- Lidar com download de áudio (formato `.ogg` diferente do Telegram)

### ISSUE-010 — Geração de PDF não testada
**Descrição:** `services/pdf.py` e `templates/rdo_default.html` existem, mas WeasyPrint tem dependências de sistema (libcairo, pango) que precisam ser instaladas separadamente e podem ser problemáticas no WSL2.
**Alternativa para MVP:** Endpoint `/rdo/preview/{obra_id}/{data}` já retorna HTML renderizado — pode ser impresso pelo browser como PDF no curto prazo.

### ISSUE-011 — Sem autenticação nas rotas
**Descrição:** Todos os endpoints CRUD são públicos. Qualquer um com acesso à URL pode ler/escrever dados.
**Solução planejada:** JWT com `obra_id` no payload. Usuário se autentica pelo telefone (OTP via Telegram/WhatsApp).

### ISSUE-012 — Sem tratamento de erros no Orchestrator para Ollama offline
**Descrição:** Se o Ollama não estiver rodando, o intent classifier lança `httpx.ConnectError` e o bot retorna mensagem de erro genérica ao usuário.
**Fix sugerido:** Fallback com regex simples para as intenções mais comuns (efetivo, clima) quando Ollama indisponível. Adicionar health check no startup da aplicação.

### ISSUE-013 — Estado de "Em Andamento" não é atualizado automaticamente
**Descrição:** Atividades com `status=INICIADA` não transitam automaticamente para `EM_ANDAMENTO` no dia seguinte. A lógica existe no RDO generator (que agrupa por data), mas o status no banco não é atualizado.
**Impacto:** Consultas diretas no banco ou na API retornam status incorreto.
**Fix:** Job agendado diário (cron) que roda `UPDATE atividades SET status='em_andamento' WHERE status='iniciada' AND data_inicio < TODAY`.

### ISSUE-014 — Sem suporte a múltiplas obras por usuário
**Descrição:** `Usuario.obra_id` é um FK único — cada usuário pertence a uma obra. Engenheiros que gerenciam múltiplas obras não são suportados.
**Solução futura:** Tabela `usuario_obras` (many-to-many) + contexto de sessão (usuário seleciona a obra ativa antes de registrar).

### ISSUE-015 — Dashboard web não implementado
**Descrição:** Não há interface para o responsável revisar o RDO do dia, corrigir registros e aprovar antes de gerar PDF.
**Stack planejado:** HTMX + FastAPI (server-side rendering, sem JS pesado). Autenticação por link mágico enviado pelo bot.

---

## Ordem sugerida para próximas sessões

1. **Fix ISSUE-001**: Script `scripts/dev-start.sh` para subir o ambiente
2. **Fix ISSUE-005 + ISSUE-006**: Corrigir imports quebrados e awaits incorretos no Orchestrator → API sobe sem erro
3. **Fix ISSUE-002 + ISSUE-003**: Fluxo de onboarding mínimo + configuração correta do Whisper → primeiro teste end-to-end no Telegram
4. **Fix ISSUE-004**: Instanciação segura do adapter
5. **ISSUE-010**: Testar geração de PDF com WeasyPrint ou migrar para alternativa
6. **ISSUE-009**: Implementar adapter WhatsApp via Evolution API
7. **ISSUE-008**: Embeddings para conclusão de atividade
8. **ISSUE-011**: Autenticação JWT
9. **ISSUE-015**: Dashboard HTMX
