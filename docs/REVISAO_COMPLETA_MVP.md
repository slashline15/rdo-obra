# Revisão completa do código — RDO Digital (MVP)

> Público-alvo: liderança de produto/negócio que está aprendendo tecnologia.
>
> Objetivo: explicar **como o sistema funciona hoje**, **o que está bom**, **o que pode quebrar o MVP** e **o que priorizar** para chegar em uma versão estável de produção.

---

## 1) Resumo executivo (sem jargão)

O projeto está em estágio **MVP funcional**: já recebe mensagens (Telegram/WhatsApp), interpreta intenção com IA, grava no banco e gera RDO em JSON/HTML (PDF parcial).

Para validação de produto isso é bom. Para operação contínua com cliente pagante, ainda faltam pilares de robustez:

- Segurança de API (autenticação/autorização).
- Confiabilidade operacional (estado não volátil, testes automatizados).
- Correção de onboarding Telegram (há bug de atributo inexistente).

**Decisão recomendada:** usar em piloto controlado, mas não escalar sem uma sprint de blindagem técnica.

---

## 2) Leitura arquitetural do projeto

## 2.1 Fluxo ponta a ponta

1. Canal recebe mensagem (adapter Telegram/WhatsApp).
2. Adapter converte para tipo interno `IncomingMessage`.
3. `Orchestrator` identifica usuário/obra.
4. Se áudio: chama transcrição.
5. Classificador decide categoria + dados.
6. Registro é salvo no módulo apropriado (atividade, efetivo etc.).
7. `RelationEngine` executa regras cruzadas (clima, atraso, pendência).
8. Sistema responde no mesmo canal.

## 2.2 Camadas técnicas

- **Entradas/saídas:** `app/adapters/*`
- **Coordenação do fluxo:** `app/core/orchestrator.py`
- **Regras de negócio cruzadas:** `app/core/relations.py`
- **IA (intenção + transcrição):** `app/services/intent.py`, `app/services/transcription.py`
- **Persistência:** `app/models.py`, `app/database.py`
- **API e rotas:** `app/main.py`, `app/routes/*`
- **RDO:** `app/services/rdo_generator.py`

---

## 3) Revisão por módulo (o que está bom / risco principal)

| Módulo | Situação atual | Risco principal |
|---|---|---|
| `main.py` / bootstrap | API sobe com routers e healthcheck | CORS totalmente aberto |
| Adapters Telegram/WhatsApp | Telegram funcional; WhatsApp parcial | Falta resiliência/homologação WhatsApp |
| Orchestrator | Boa separação por intenção e registro | Estado de callback em memória (volátil) |
| RelationEngine | Regras de impacto úteis ao negócio | Sem job de rotina integrado por scheduler |
| Models | Domínio rico para obra real | Defaults JSON mutáveis e validação parcial |
| Routes CRUD | Cobertura ampla de entidades | Sem autenticação |
| IA (intent/transcription) | Estratégia híbrida (regex + LLM) | Ambiguidade semântica em conclusão |
| RDO generator | JSON/HTML funcional, PDF pronto para testar | Dependência de ambiente WeasyPrint |

---

## 4) Evidências técnicas (mapa objetivo)

> Esta seção liga cada achado a pontos concretos do código, para facilitar auditoria.

1. **Sem autenticação nas rotas / API pública**
   - Não há dependência de auth nos routers e o status do README confirma “Autenticação: não implementado”.

2. **CORS aberto**
   - `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]` no app principal.

3. **Bug de onboarding Telegram (`user.funcao`)**
   - Fluxo `/start` tenta renderizar `user.funcao`, atributo inexistente no model `Usuario`.

4. **Estado volátil para callbacks**
   - `_textos_pendentes` é dicionário em memória no orchestrator.

5. **Onboarding com auto-vinculação arriscada**
   - `/start` pega primeiro usuário com regex de telefone e sobrescreve telefone com `chat_id`.

6. **Sem migração versionada**
   - Banco é iniciado por `Base.metadata.create_all(...)` (sem Alembic).

7. **Fallback parcial de IA**
   - `classify_intent` usa regex + chamada Ollama + fallback; robustez existe, mas extração fica básica quando LLM falha.

8. **WhatsApp ainda parcial**
   - README e adapter mostram suporte incompleto/stub para produção.

---

## 5) Achados priorizados

## P0 (bloqueia escala com segurança)

### P0.1 Segurança/API
Sem auth e sem isolamento por perfil/obra.

**Impacto:** risco direto de exposição/alteração indevida de dados.

### P0.2 Onboarding Telegram com bug de runtime
Uso de atributo inexistente no `/start`.

**Impacto:** quebra no primeiro contato do usuário.

### P0.3 Estado em memória para fluxo crítico
Texto pendente para botão inline expira em reinício.

**Impacto:** perda de contexto e frustração de uso.

### P0.4 Auto-vinculação de usuário sem prova de identidade
Sobrescreve telefone de usuário existente com chat de quem iniciou.

**Impacto:** risco de atribuição incorreta de registros de obra.

---

## P1 (importante para estabilidade)

- Introduzir migrações com Alembic.
- Criar testes automatizados de fumaça e regressão.
- Ajustar política de erro (não expor exceções internas ao usuário final).
- Padronizar logging com correlação (`obra_id`, `usuario`, `intent`, `confidence`).

---

## P2 (qualidade evolutiva)

- Melhorar matching semântico de conclusão de atividade.
- Fortalecer validações de domínio (enums/constraints mais rígidos).
- Converter defaults JSON para `default=dict`.
- Consolidar transações por mensagem para reduzir inconsistência parcial.

---

## 6) Plano prático para fechar MVP

## Sprint 1 (1 semana) — blindagem mínima
1. Corrigir `/start` Telegram.
2. JWT básico + proteção de rotas.
3. CORS por ambiente.
4. Persistir `_textos_pendentes` em Redis/tabela temporária.
5. Testes de fumaça: webhook Telegram, registro atividade, RDO JSON.

## Sprint 2 (1 semana) — robustez
1. Alembic + primeira migração baseline.
2. Logging estruturado.
3. Política de fallback/retry para IA.
4. Onboarding por código de convite.

## Sprint 3 (1 semana) — qualidade de produto
1. Matching semântico de conclusão.
2. Mini dashboard de revisão antes do PDF.
3. Métricas operacionais (latência, acurácia, retrabalho).

---

## 7) Trilha de estudo (não programador)

Ordem recomendada de leitura:

1. `README.md` (visão de produto e setup).
2. `app/main.py` (como os módulos entram na API).
3. `app/core/orchestrator.py` (fluxo que gera valor).
4. `app/services/intent.py` (decisão da IA).
5. `app/core/relations.py` (regras de negócio automáticas).
6. `app/models.py` (estrutura de dados da operação).
7. `app/services/rdo_generator.py` (saída final do RDO).

---

## 8) Decisão de produto sugerida

- **Piloto controlado:** pode avançar.
- **Escala operacional contínua:** aguardar conclusão dos itens P0/P1.

---

## 9) Glossário rápido

- **MVP:** versão mínima para validar valor.
- **Webhook:** endpoint que recebe eventos de terceiros.
- **Orchestrator:** coordenador central do fluxo.
- **Fallback:** plano B quando serviço principal falha.
- **JWT:** token de autenticação para API.
- **Migração de banco:** histórico versionado de alterações no schema.
