# Arquitetura RDO Digital v2

## Princípios
1. **Modular ao máximo** — cada funcionalidade é um módulo independente
2. **Modelos locais** — Ollama para classificação, Whisper local para transcrição
3. **Orquestrador central** — coordena módulos e mantém relações lógicas
4. **Multi-canal** — WhatsApp + Telegram via adapter pattern
5. **PostgreSQL** — desde o início, preparado para escalar

## Arquitetura de Módulos

```
┌─────────────────────────────────────────────────┐
│                  ADAPTERS (I/O)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Telegram │  │ WhatsApp │  │  Web/API     │  │
│  │  Bot API │  │ Evolution│  │  Dashboard   │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │          │
│       └──────────────┼───────────────┘          │
│                      ▼                          │
│         ┌────────────────────────┐              │
│         │    ORQUESTRADOR        │              │
│         │  (message_router.py)   │              │
│         │  - Identifica usuário  │              │
│         │  - Roteia para módulo  │              │
│         │  - Gerencia estado     │              │
│         │  - Valida relações     │              │
│         └───────────┬────────────┘              │
│                     │                           │
│    ┌────────────────┼───────────────────┐       │
│    ▼                ▼                   ▼       │
│ ┌──────┐  ┌──────────────┐  ┌───────────────┐  │
│ │ STT  │  │   INTENT     │  │   RESPONSE    │  │
│ │Whisper│  │  CLASSIFIER  │  │   FORMATTER   │  │
│ │local │  │  (Ollama)    │  │  (confirmação)│  │
│ └──┬───┘  └──────┬───────┘  └───────────────┘  │
│    │             │                              │
│    └─────────────┘                              │
│                  │                              │
│    ┌─────────────┼──────────────────────┐       │
│    ▼             ▼            ▼         ▼       │
│ ┌───────┐ ┌──────────┐ ┌────────┐ ┌────────┐   │
│ │ATIVID.│ │ EFETIVO  │ │MATERIAL│ │ CLIMA  │   │
│ │Module │ │  Module  │ │ Module │ │ Module │   │
│ ├───────┤ ├──────────┤ ├────────┤ ├────────┤   │
│ │EQUIP. │ │ANOTAÇÕES │ │ FOTOS  │ │CONSULTA│   │
│ │Module │ │  Module  │ │ Module │ │ Module │   │
│ └───┬───┘ └────┬─────┘ └───┬────┘ └───┬────┘   │
│     │          │            │          │        │
│     └──────────┼────────────┘          │        │
│                ▼                       │        │
│    ┌───────────────────────┐           │        │
│    │   RELATION ENGINE     │◄──────────┘        │
│    │  (lógica de negócio)  │                    │
│    │  - Atividade impacta  │                    │
│    │    cronograma         │                    │
│    │  - Clima → atraso     │                    │
│    │  - Material pendente  │                    │
│    │    → anotação         │                    │
│    └───────────┬───────────┘                    │
│                ▼                                │
│    ┌───────────────────────┐                    │
│    │     PostgreSQL        │                    │
│    │  + pgvector           │                    │
│    │  (embeddings)         │                    │
│    └───────────────────────┘                    │
│                                                 │
│    ┌───────────────────────┐                    │
│    │   RDO GENERATOR       │                    │
│    │  - Coleta dados do dia│                    │
│    │  - Aplica template    │                    │
│    │  - Gera PDF           │                    │
│    │  - Envia por canal    │                    │
│    └───────────────────────┘                    │
└─────────────────────────────────────────────────┘
```

## Fluxo de uma Mensagem

1. Adapter recebe mensagem (Telegram/WhatsApp)
2. Normaliza para formato interno `IncomingMessage`
3. Orquestrador identifica usuário e obra
4. Se áudio → STT (Whisper local)
5. Intent Classifier (Ollama) → identifica categoria + extrai dados
6. Módulo específico valida e prepara registro
7. Relation Engine verifica impactos cruzados
8. Salva no PostgreSQL
9. Response Formatter gera confirmação
10. Adapter envia resposta no canal de origem

## Lógica de Atividades (Serviços)

### Estados
```
INICIADA → EM ANDAMENTO → CONCLUÍDA
                ↑              │
                └──────────────┘ (reaberta se necessário)
```

### Regras
- Atividade tem `data_inicio` e `data_fim` (prevista e real)
- Entre início e fim, aparece automaticamente como "em andamento" nos RDOs
- Descrição é redigida tecnicamente pelo LLM e mantida consistente
- Se dia improdutivo (clima), Relation Engine registra atraso
- Template PDF agrupa: Iniciadas | Em Andamento | Concluídas

### Exemplo
Dia 1: "Começamos a concretagem da laje do 2º pav"
→ Atividade criada: "Execução de concretagem da laje do 2º pavimento tipo" | status: INICIADA

Dia 2: (nenhuma mensagem sobre isso)
→ RDO mostra automaticamente em "Em Andamento"

Dia 3: "Terminamos a concretagem do segundo andar"
→ Atividade atualizada: status: CONCLUÍDA | data_fim_real: hoje

Dia 4 (chuva): "Choveu o dia todo"
→ Clima registrado + Relation Engine marca atraso nas atividades em andamento

## Relações entre Tabelas

```
clima.improdutivo = true
    → atividades em andamento recebem flag de atraso
    → anotação automática: "Dia improdutivo por chuva"

material.tipo = "pendente" AND material.responsavel = "cliente"
    → anotação automática: "Material do cliente pendente: {material}"
    → se atrasado, impacto no cronograma

atividade.concluida
    → verifica se próxima atividade dependente pode iniciar

equipamento.saida
    → verifica se alguma atividade em andamento dependia dele
```

## Stack de Produção

| Componente | Tecnologia | Custo |
|-----------|-----------|-------|
| Backend | FastAPI (Python) | — |
| Database | PostgreSQL + pgvector | incluído no VPS |
| LLM | Ollama (qwen2.5:7b ou similar) | CPU no VPS |
| STT | whisper.cpp ou Groq | ~grátis |
| Telegram | Bot API oficial | grátis |
| WhatsApp | Evolution API (self-hosted) | grátis |
| PDF | WeasyPrint | — |
| Dashboard | HTMX + FastAPI | — |
| VPS | Hetzner ARM 4GB | ~R$ 40/mês |
