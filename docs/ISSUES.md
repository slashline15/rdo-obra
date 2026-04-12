# ISSUES.md — Problemas Conhecidos e Pendências Técnicas

> Atualizado: 2026-04-03
> Estado: MVP funcional. Primeiro teste end-to-end no Telegram concluído com sucesso.

---

## Resolvidos nesta sessão (2026-04-03)

### ISSUE-003 — `transcription.py` não lia configuração do `.env` ✅
**Fix:** Substituído `os.getenv()` por `settings` do pydantic-settings. Agora lê corretamente `WHISPER_API_KEY` e `OPENAI_API_KEY`.

### ISSUE-004 — `TelegramAdapter` instanciado fora do request ✅
**Fix:** Movido para dentro do endpoint. Adicionado handler de `/start` com auto-vinculação de chat_id e handler de `callback_query` para botões inline.

### ISSUE-005 — `routes/servicos.py` referência ao modelo antigo ✅
**Status:** Falso positivo — o arquivo já usa `Atividade` corretamente, apenas o nome do arquivo é legado.

### ISSUE-006 — `await` em métodos síncronos do Orchestrator ✅
**Status:** Falso positivo — os métodos `_registrar_*` são chamados sem `await`, o código já estava correto.

### ISSUE-002 — Usuário sem `telegram_chat_id` mapeado ✅
**Fix:** Implementado fluxo `/start` no webhook que vincula automaticamente o chat_id do Telegram ao primeiro usuário disponível no banco.

### Bug: LLM retornava "categoria" como intent literal
**Causa:** Prompt usava `"intent": "categoria"` como placeholder e o modelo copiava.
**Fix:** Prompt reescrito com exemplos concretos + pré-filtro por keywords + validação de intents.

### Bug: `equipamentos.tipo` VARCHAR(15) estourava com dados do LLM
**Causa:** LLM invertia campos `tipo` e `equipamento`, colocando nome do equipamento no campo `tipo`.
**Fix:** Coluna ampliada para VARCHAR(30) + validação no orchestrator que detecta e corrige inversão.

---

## Problemas conhecidos (pendentes)

### ISSUE-001 — PostgreSQL não sobe automaticamente no WSL2
**Descrição:** No WSL2/Kali, `sudo service postgresql start` funciona mas precisa de senha sudo.
**Workaround:** Rodar manualmente antes de iniciar a API.
**Melhoria:** Criar script `scripts/dev-start.sh` que sobe PostgreSQL + Ollama + API.

### ISSUE-007 — Relation Engine não é chamado para `atividade`
**Descrição:** `_registrar_atividade()` cria a atividade mas não verifica dependências via Relation Engine.
**Impacto:** Baixo para MVP. Atividades com `atividade_pai_id` não bloqueiam automaticamente.

### ISSUE-008 — Matching semântico para conclusão de atividade
**Status:** resolvido em 2026-04-11.
**Descrição anterior:** `_concluir_atividade()` usava matching por palavras-chave simples. Frases ambíguas podiam concluir a atividade errada.
**Solução aplicada:** `atividade_embeddings` + pgvector + busca semântica com fallback para escolha explícita.

### ISSUE-009 — Adapter WhatsApp não implementado
**Status:** resolvido em 2026-04-11.
**Descrição anterior:** `app/adapters/whatsapp.py` era um stub. Evolution API requer instância self-hosted.
**Solução aplicada:** `WhatsAppAdapter` com webhook canônico em `/whatsapp/webhook`, menus textuais e suporte a reply/quote.

### ISSUE-010 — Geração de PDF não testada
**Descrição:** Template HTML existe. WeasyPrint tem dependências de sistema que podem ser problemáticas no WSL2.
**Alternativa:** Endpoint `/rdo/preview/{obra_id}/{data}` já retorna HTML renderizado.

### ISSUE-011 — Sem autenticação nas rotas
**Descrição:** Todos os endpoints são públicos. Qualquer um com a URL pode ler/escrever dados.
**Solução planejada:** JWT com `obra_id` no payload.

### ISSUE-012 — Sem tratamento para Ollama offline
**Descrição:** Se Ollama cair, o intent classifier agora faz fallback para keywords (implementado em 2026-04-03), mas a extração de dados fica básica.

### ISSUE-013 — Status "Em Andamento" não atualiza automaticamente
**Descrição:** Atividades com `status=INICIADA` não transitam para `EM_ANDAMENTO` no dia seguinte.
**Fix:** Job agendado diário.

### ISSUE-014 — Sem suporte a múltiplas obras por usuário
**Descrição:** `Usuario.obra_id` é FK único. Engenheiros com múltiplas obras não são suportados.

### ISSUE-015 — Dashboard web não implementado
**Descrição:** Não há interface para revisar, corrigir e aprovar o RDO antes de gerar PDF.

### ISSUE-016 — Matching de conclusão impreciso (novo)
**Status:** resolvido em 2026-04-11.
**Descrição anterior:** Ao concluir atividade, o sistema buscava por palavras-chave simples e podia concluir a atividade errada quando havia termos em comum.
**Solução aplicada:** Embeddings com pgvector e menu de escolha explícita quando a confiança não é alta o suficiente.

### ISSUE-017 — Botão de callback expira se API reiniciar (novo)
**Status:** resolvido em 2026-04-11.
**Descrição anterior:** Textos pendentes para callbacks de botões inline eram armazenados em memória (dict). Se a API reiniciasse entre a mensagem e o clique, o texto se perdia.
**Solução aplicada:** `conversation_states` em PostgreSQL com espelho em Redis e consumo idempotente por `state_token`.

---

## Próximas sessões — roadmap sugerido

### Sessão 2: Robustez do fluxo de voz
1. **Testar transcrição de áudio real** — enviar mensagem de voz no Telegram e verificar Whisper
2. **Melhorar matching de conclusão** — score ponderado por relevância dos termos
3. **Script `dev-start.sh`** — sobe PostgreSQL + Ollama + API com um comando
4. **Validação de dados do LLM** — outros campos além de equipamento.tipo podem estourar

### Sessão 3: RDO completo
1. **Testar geração de RDO** — endpoint `/rdo/preview/{obra_id}/{data}` com dados reais
2. **PDF via WeasyPrint** — instalar dependências e testar
3. **Envio de PDF pelo bot** — `/rdo` no Telegram gera e envia o PDF do dia

### Sessão 4: Qualidade e confiabilidade
1. **Testes automatizados** — pytest para keyword_classify, orchestrator, routes
2. **Logging estruturado** — registrar todas as classificações para análise
3. **Métricas** — acurácia do classifier, tempo de resposta

### Sessão 5: Infraestrutura
1. **Cloudflare Tunnel permanente** — `api.engdaniel.org` → localhost
2. **Docker Compose** — PostgreSQL + Ollama + API em containers
3. **Deploy em VPS** — primeira versão em produção

### Sessão 6+: Features avançadas
1. **Autenticação JWT** — onboarding seguro via Telegram
2. **Dashboard HTMX** — revisão e aprovação de RDO
3. **WhatsApp via Evolution API**
4. **Embeddings (pgvector)** — matching semântico para conclusão de atividades
5. **Multi-obra** — tabela many-to-many para usuários
