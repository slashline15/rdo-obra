---
Criado: 2026-04-11
tags:
  - rdo-digital
  - canteiro-digital
  - estrategia
  - reestruturacao
  - relatorio
  - v2
Status:
  - Em revisao
Modificado: 2026-04-11
---

# Do RDO Digital ao Canteiro Digital
## Relatorio Estrateégico de Reestruturacao

---

## 1. Diagnostico do estado atual

### O que existe e funciona
#pendencias 

O RDO Digital ja possui um nucleo solido:

| Camada          | Tecnologia                               | Status            | V2  | tag                |
| --------------- | ---------------------------------------- | ----------------- | --- | ------------------ |
| Backend/API     | FastAPI + PostgreSQL (15 tabelas)        | Avancado          | 30% | #pendencia_critica |
| IA local        | Ollama (qwen2.5:7b) + Whisper (OpenAI)   | Funcional         | 50% |                    |
| Bot Telegram    | Recebe audio/texto, classifica, registra | Funcional         | 60% |                    |
| Bot WhatsApp    | Estrutura criada (Evolution API)         | Incompleto        | 20% | #pendencia_media   |
| Painel web      | React + TypeScript + Tailwind            | Funcional parcial | 20% |                    |
| PDF             | WeasyPrint + Jinja2                      | Funcional         | 0%  | #pendencia_media   |
| Autenticacao    | JWT + 3 niveis de acesso                 | Completo          | 80% |                    |
| Relation Engine | 3 regras automaticas ativas              | Funcional         |     | #pendencia_media   |
| Auditoria       | audit_log + soft delete                  | Completo          |     |                    |
- [ ] Atualizar status do database🔺  
### Dividas tecnicas criticas (resolver antes de escalar)

1. **Estado de mensagens em RAM** — se o servidor reiniciar, contexto se perde. Precisa de Redis ou persistencia no banco. #pendencia_critica 
	1. [ ] Adicionar cache com redis 🔺 
	2. [ ] Persistência de dados PostgreSQL 🔺 
2. **Busca de atividades por palavras-chave** — pode concluir atividade errada. Precisa de embeddings (pgvector). #pendencia_critica 
	1. [ ] Adicionar embbedins de dados para busca semântica🔺 
		1. [ ] Otimizar e testar relation engine🔺 
	2. [ ] Adicionar dados fakes retroativos🔼 
3. **WhatsApp nao finalizado** — canal mais importante do mercado.
	1. [ ] Integrar Whatsapp🔼 

### Gap estrategico

O sistema sabe **o que foi feito** mas nao sabe **o que deveria ter sido feito**, **quanto custou**, **quem fez** (de forma rastreavel) nem **onde estao os documentos tecnicos**. **Para se tornar um Canteiro Digital, precisa fechar esses 4 gaps**.
- 

---

## 2. Visao arquitetural: Canteiro Digital

```
                    ┌──────────────────────────────────────────────┐
                    │            CANTEIRO DIGITAL                  │
                    │                                              │
 WhatsApp ─────┐   │  ┌─────────┐   ┌────────────┐   ┌────────┐  │
 Telegram ─────┼──→│  │ RDO     │──→│ CRONOGRAMA │──→│ GANTT  │  │
 Painel Web ───┤   │  │ DIGITAL │   │ (previsto  │   │ REAL   │  │
 Upload docs ──┘   │  │ (dia a  │   │  vs real)  │   │        │  │
                    │  │  dia)   │   └────────────┘   └────────┘  │
                    │  └────┬────┘          │                      │
                    │       │               ▼                      │
                    │       │     ┌──────────────────┐             │
                    │       │     │ FINANCEIRO       │             │
                    │       │     │ (orcamento,      │             │
                    │       │     │  custos, NFs,    │             │
                    │       │     │  curva S, ABC)   │             │
                    │       │     └──────────────────┘             │
                    │       │               │                      │
                    │       ▼               ▼                      │
                    │  ┌─────────┐   ┌──────────────┐             │
                    │  │ EQUIPE  │   │ EMPREITEIRAS │             │
                    │  │ (ponto, │   │ (contratos,  │             │
                    │  │  EPI,   │   │  medicoes,   │             │
                    │  │  hist.) │   │  termos)     │             │
                    │  └─────────┘   └──────────────┘             │
                    │       │               │                      │
                    │       ▼               ▼                      │
                    │  ┌────────────────────────────┐              │
                    │  │ DOCUMENTOS TECNICOS        │              │
                    │  │ (CAD → SVG/HTML, QR Code,  │              │
                    │  │  cloud storage, versionam.) │              │
                    │  └────────────────────────────┘              │
                    │                  │                            │
                    │                  ▼                            │
                    │  ┌────────────────────────────┐              │
                    │  │ RELATION ENGINE v2         │              │
                    │  │ (regras cruzadas entre     │              │
                    │  │  todos os modulos)         │              │
                    │  └────────────────────────────┘              │
                    │                  │                            │
                    │                  ▼                            │
                    │  ┌────────────────────────────┐              │
                    │  │ DASHBOARDS + KPIs + PDF    │              │
                    │  └────────────────────────────┘              │
                    └──────────────────────────────────────────────┘
```

---

## 3. Modulo B — Cronograma (integracao com planejamento real)

### 3.1. Objetivo

Conectar o **planejado** (cronograma importado) com o **executado** (dados do RDO), gerando informacoes documentaveis e auditaveis sobre produtividade, atrasos e adiantamentos.

### 3.2. Tabelas propostas

```sql
-- Tabela principal: cada tarefa do cronograma importado
cronograma_tarefas (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    baseline_id         FK → cronograma_baselines,
    codigo_wbs          VARCHAR,          -- "1.2.3.1" (estrutura analitica)
    nome                VARCHAR NOT NULL,
    descricao           TEXT,
    data_inicio_prevista DATE NOT NULL,
    data_fim_prevista    DATE NOT NULL,
    duracao_dias        INTEGER,
    folga_total         INTEGER,          -- dias de folga (float)
    folga_livre         INTEGER,
    responsavel         VARCHAR,
    predecessora_id     FK → cronograma_tarefas,  -- dependencia
    tipo_vinculo        VARCHAR DEFAULT 'TI',      -- TI, TT, II, IT
    caminho_critico     BOOLEAN DEFAULT FALSE,
    atividade_rdo_id    FK → atividades,  -- vinculo com atividade registrada
    peso_percentual     DECIMAL(5,2),     -- peso para curva S fisica
    unidade_medida      VARCHAR,          -- m2, m3, un, vb
    quantidade_prevista DECIMAL(12,2),
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

-- Baseline: "fotografia" do cronograma em um momento
cronograma_baselines (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    versao              VARCHAR NOT NULL,  -- "v1", "v2", "replanejamento-jun26"
    data_import         TIMESTAMP NOT NULL,
    importado_por       FK → usuarios,
    arquivo_original    VARCHAR,           -- caminho do arquivo fonte
    formato_origem      VARCHAR,           -- "xlsx", "mpp_xml", "csv", "json"
    observacoes         TEXT,
    ativo               BOOLEAN DEFAULT TRUE,  -- apenas 1 ativo por vez
    dados_snapshot_json JSONB              -- snapshot completo para auditoria
);

-- Progresso real: registrado via RDO dia a dia
cronograma_progresso (
    id                  SERIAL PRIMARY KEY,
    tarefa_id           FK → cronograma_tarefas,
    diario_id           FK → diarios_dia,
    data_registro       DATE NOT NULL,
    percentual_anterior DECIMAL(5,2),
    percentual_novo     DECIMAL(5,2),
    quantidade_executada DECIMAL(12,2),
    registrado_por      FK → usuarios,
    fonte               VARCHAR DEFAULT 'rdo',  -- 'rdo', 'manual', 'ia'
    observacoes         TEXT,
    created_at          TIMESTAMP,
    UNIQUE(tarefa_id, data_registro)
);

-- Desvios: log auditavel de cada desvio detectado
cronograma_desvios (
    id                  SERIAL PRIMARY KEY,
    tarefa_id           FK → cronograma_tarefas,
    tipo_desvio         VARCHAR NOT NULL,  -- 'atraso', 'adiantamento', 'replanejamento'
    dias_desvio         INTEGER NOT NULL,
    motivo              VARCHAR,           -- 'chuva', 'falta_material', 'falta_mao_obra'
    dia_improdutivo_id  FK → dias_improdutivos,
    impacto_caminho_critico BOOLEAN DEFAULT FALSE,
    data_deteccao       DATE NOT NULL,
    gerado_por          VARCHAR DEFAULT 'relation_engine',
    created_at          TIMESTAMP
);
```

### 3.3. Como o Gantt faz sentido logico

Para o Gantt ser documentavel e auditavel:

1. **Baseline imutavel** — o cronograma original importado nunca e alterado. Cada replanejamento gera um novo baseline com versao incrementada.
2. **Progresso rastreavel** — cada atualizacao de percentual vem vinculada a um `diario_id` (quem reportou, quando, de onde).
3. **Desvios com causa** — cada atraso ou adiantamento e registrado com motivo (chuva, falta de material, falta de mao de obra). O `dia_improdutivo_id` vincula diretamente ao registro climatico.
4. **Caminho critico recalculado** — quando uma tarefa no caminho critico atrasa, o sistema propaga o impacto para as tarefas dependentes e registra isso em `cronograma_desvios`.

**Visualizacao no Gantt:**
```
Tarefa                    | Baseline (cinza)   | Real (cor)         | Status
─────────────────────────┼────────────────────┼────────────────────┼────────
Armacao laje 3o pav.      | ████████████       | ████████████       | No prazo
Formas borda alcapao      | ████████           | ████████████       | +2 dias
Caixa passagem eletrica   | ██████             | ██████████         | +3 dias (CRITICO)
Esperas hidraulicas       | ████████████       | █████████████      | +1 dia
```

- Barra cinza = baseline (previsto original)
- Barra colorida = real (verde = no prazo, amarelo = atencao, vermelho = critico)
- Sobreposicao visual mostra exatamente onde o desvio ocorre

### 3.4. Fluxo de integracao com o RDO

```
Encarregado: "Terminamos de armar a laje do 3o andar"
    │
    ▼
IA extrai: atividade "armacao de laje", status "concluida"
    │
    ▼
Orquestrador busca atividade no banco (embeddings/pgvector)
    │
    ▼
Atividade encontrada → verifica se tem cronograma_tarefa_id vinculado
    │
    ▼
Se sim:
    ├── Atualiza percentual_concluido na atividade (100%)
    ├── Insere registro em cronograma_progresso
    ├── Calcula desvio: data_termino_real vs data_fim_prevista
    ├── Se desvio > 0 → insere em cronograma_desvios
    ├── Se tarefa no caminho critico → propaga para dependentes
    └── Relation Engine gera anotacao e/ou alerta
```

### 3.5. KPIs de cronograma

| KPI | Formula | Uso |
|-----|---------|-----|
| SPI (Schedule Performance Index) | % executado / % previsto | > 1 = adiantado, < 1 = atrasado |
| Desvio acumulado | SUM(dias_desvio) por tarefa | Impacto total no prazo |
| Aderencia ao cronograma | tarefas no prazo / total tarefas | Saude geral do planejamento |
| Dias improdutivos acumulados | SUM(dias_improdutivos) | Justificativa documentada de atrasos |
| Velocidade de producao | quantidade_executada / dias_trabalhados | Produtividade real por atividade |

---

## 4. Modulo C — Controle Financeiro

### 4.1. Objetivo

Integrar planilha orcamentaria, controle de custos e metas para gerar KPIs financeiros uteis (Curva S, ABC, cronograma fisico-financeiro, previsao de gastos) que alimentem inclusive o balancete.

### 4.2. Tabelas propostas

```sql
-- Planilha orcamentaria importada
orcamento_itens (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    orcamento_versao_id FK → orcamento_versoes,
    codigo_servico      VARCHAR NOT NULL,      -- "01.02.003"
    descricao           TEXT NOT NULL,
    unidade             VARCHAR,               -- m2, m3, kg, vb, un
    quantidade          DECIMAL(12,4),
    preco_unitario      DECIMAL(12,4),
    bdi_percentual      DECIMAL(5,2),
    total_sem_bdi       DECIMAL(14,2),
    total_com_bdi       DECIMAL(14,2),
    grupo               VARCHAR,               -- "Estrutura", "Instalacoes"
    subgrupo            VARCHAR,               -- "Concreto", "Forma", "Aco"
    cronograma_tarefa_id FK → cronograma_tarefas,  -- vinculo com cronograma
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

-- Versionamento do orcamento
orcamento_versoes (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    versao              VARCHAR NOT NULL,
    data_import         TIMESTAMP,
    importado_por       FK → usuarios,
    arquivo_original    VARCHAR,
    tipo                VARCHAR,    -- 'orcamento_base', 'aditivo', 'replanilhamento'
    valor_total         DECIMAL(14,2),
    ativo               BOOLEAN DEFAULT TRUE,
    observacoes         TEXT
);

-- Notas fiscais / comprovantes de gasto
notas_fiscais (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    numero_nf           VARCHAR,
    serie               VARCHAR,
    fornecedor_id       FK → fornecedores,
    data_emissao        DATE NOT NULL,
    data_vencimento     DATE,
    data_pagamento      DATE,
    valor_total         DECIMAL(14,2) NOT NULL,
    valor_retencao      DECIMAL(14,2) DEFAULT 0,  -- ISS, INSS retido
    valor_liquido       DECIMAL(14,2),
    categoria           VARCHAR,    -- 'material', 'servico', 'equipamento', 'mao_obra'
    arquivo_path        VARCHAR,    -- foto ou PDF da NF
    ocr_processado      BOOLEAN DEFAULT FALSE,
    ocr_dados_json      JSONB,      -- dados extraidos pelo OCR
    status              VARCHAR DEFAULT 'pendente', -- 'pendente', 'aprovada', 'paga', 'cancelada'
    aprovado_por        FK → usuarios,
    registrado_por      FK → usuarios,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

-- Vinculo NF ↔ item do orcamento (N:N)
nf_orcamento_vinculo (
    id                  SERIAL PRIMARY KEY,
    nota_fiscal_id      FK → notas_fiscais,
    orcamento_item_id   FK → orcamento_itens,
    valor_alocado       DECIMAL(14,2),   -- quanto dessa NF corresponde a esse item
    observacoes         TEXT
);

-- Fornecedores
fornecedores (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR NOT NULL,
    cnpj                VARCHAR UNIQUE,
    contato_nome        VARCHAR,
    contato_telefone    VARCHAR,
    contato_email       VARCHAR,
    categoria           VARCHAR,    -- 'material', 'servico', 'equipamento', 'mao_obra'
    avaliacao           INTEGER,    -- 1 a 5
    ativo               BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP
);

-- Medicoes mensais (para empreiteiras e para o cliente)
medicoes (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    empreiteira_id      FK → empreiteiras,  -- NULL se for medicao para o cliente
    competencia         VARCHAR NOT NULL,    -- "2026-04"
    tipo                VARCHAR,             -- 'empreiteira', 'cliente', 'interna'
    valor_acumulado_anterior DECIMAL(14,2),
    valor_periodo       DECIMAL(14,2),
    valor_acumulado     DECIMAL(14,2),
    percentual_fisico   DECIMAL(5,2),
    aprovado_por        FK → usuarios,
    status              VARCHAR DEFAULT 'rascunho',  -- 'rascunho', 'aprovada', 'paga'
    arquivo_pdf         VARCHAR,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

-- Itens da medicao
medicao_itens (
    id                  SERIAL PRIMARY KEY,
    medicao_id          FK → medicoes,
    orcamento_item_id   FK → orcamento_itens,
    quantidade_medida   DECIMAL(12,4),
    valor_medido        DECIMAL(14,2),
    percentual_executado DECIMAL(5,2),
    observacoes         TEXT
);

-- Metas de desembolso (planejamento de gastos por periodo)
metas_desembolso (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    competencia         VARCHAR NOT NULL,    -- "2026-04"
    valor_previsto      DECIMAL(14,2),
    valor_realizado     DECIMAL(14,2) DEFAULT 0,
    categoria           VARCHAR,    -- 'material', 'servico', 'equipamento', 'mao_obra', 'geral'
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP,
    UNIQUE(obra_id, competencia, categoria)
);
```

### 4.3. KPIs financeiros

| KPI | Formula / Fonte | Uso pratico |
|-----|-----------------|-------------|
| **Curva S fisica** | percentual_fisico acumulado ao longo do tempo (de `cronograma_progresso`) | Mostra evolucao fisica da obra vs planejado |
| **Curva S financeira** | valor gasto acumulado ao longo do tempo (de `notas_fiscais`) vs `metas_desembolso` | Mostra evolucao de gastos vs orcado |
| **CPI (Cost Performance Index)** | valor_orcado_trabalho_realizado / valor_real_gasto | > 1 = economia, < 1 = estouro |
| **Curva ABC** | Ordenar `orcamento_itens` por valor total desc, acumular % | Identifica os 20% dos itens que representam 80% do custo |
| **Cronograma fisico-financeiro** | Cruzamento de `cronograma_progresso` com `metas_desembolso` por competencia | Uma unica visualizacao: quanto deveria ter gasto vs quanto gastou, e quanto deveria ter executado vs quanto executou |
| **Previsao de gastos (EAC)** | orcamento_total / CPI | Estimativa do custo final baseado no desempenho atual |
| **Desvio orcamentario** | (realizado - previsto) / previsto * 100 | % de estouro ou economia por item/grupo |

### 4.4. Cronograma fisico-financeiro (a visualizacao mais util)

```
Mes     | Fisico Prev | Fisico Real | Financ Prev  | Financ Real  | SPI  | CPI
────────┼─────────────┼─────────────┼──────────────┼──────────────┼──────┼─────
Jan/26  | 5%          | 4%          | R$ 50.000    | R$ 55.000    | 0.80 | 0.91
Fev/26  | 15%         | 12%         | R$ 150.000   | R$ 160.000   | 0.80 | 0.94
Mar/26  | 30%         | 28%         | R$ 300.000   | R$ 310.000   | 0.93 | 0.97
Abr/26  | 45%         | 40%         | R$ 450.000   | R$ 480.000   | 0.89 | 0.94
```

Essa tabela, gerada automaticamente a partir dos dados do RDO + cronograma + NFs, alimenta diretamente o balancete mensal e facilita a prestacao de contas ao cliente.

---

## 5. Modulo E — Documentos Tecnicos (CAD/Cloud/QR Code)

### 5.1. Objetivo

Armazenar desenhos tecnicos (plantas, cortes, detalhes) em formato acessivel por qualquer dispositivo com browser, utilizando QR Code para acesso no canteiro.

### 5.2. Tabelas propostas

```sql
-- Pranchas / documentos tecnicos
documentos_tecnicos (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    titulo              VARCHAR NOT NULL,       -- "Planta Baixa - Pavimento Tipo"
    codigo              VARCHAR,                -- "ARQ-001-R03"
    disciplina          VARCHAR,                -- 'arquitetura', 'estrutural', 'eletrica', 'hidraulica'
    tipo                VARCHAR,                -- 'planta_baixa', 'corte', 'detalhe', 'fachada'
    versao              INTEGER DEFAULT 1,
    revisao             VARCHAR,                -- "R03"
    data_emissao        DATE,
    arquivo_original    VARCHAR,                -- caminho do DWG/DXF original
    arquivo_svg         VARCHAR,                -- convertido para visualizacao web
    arquivo_html        VARCHAR,                -- pagina HTML interativa
    arquivo_thumbnail   VARCHAR,                -- miniatura para listagem
    tamanho_bytes       BIGINT,
    qrcode_uuid         UUID DEFAULT gen_random_uuid(),  -- identificador unico para QR
    qrcode_url          VARCHAR,                -- URL curta gerada
    tags                TEXT[],                  -- ["pavimento_tipo", "laje", "3o_andar"]
    upload_por          FK → usuarios,
    ativo               BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

-- Historico de revisoes
documento_revisoes (
    id                  SERIAL PRIMARY KEY,
    documento_id        FK → documentos_tecnicos,
    revisao_anterior    VARCHAR,
    revisao_nova        VARCHAR,
    motivo              TEXT,
    arquivo_anterior    VARCHAR,   -- preserva o arquivo da revisao anterior
    registrado_por      FK → usuarios,
    created_at          TIMESTAMP
);

-- Vinculo documento ↔ atividade (uma prancha pode ser relevante para varias atividades)
documento_atividade_vinculo (
    id                  SERIAL PRIMARY KEY,
    documento_id        FK → documentos_tecnicos,
    atividade_id        FK → atividades,
    cronograma_tarefa_id FK → cronograma_tarefas
);

-- Log de acessos (quem escaneou o QR e quando)
documento_acessos (
    id                  SERIAL PRIMARY KEY,
    documento_id        FK → documentos_tecnicos,
    usuario_id          FK → usuarios,       -- NULL se acesso anonimo
    ip_address          VARCHAR,
    user_agent          VARCHAR,
    acesso_via          VARCHAR DEFAULT 'qrcode',  -- 'qrcode', 'painel', 'link_direto'
    created_at          TIMESTAMP
);
```

### 5.3. Pipeline de conversao CAD → Web

```
DWG/DXF (upload pelo painel)
    │
    ▼
Conversao server-side (LibreCAD CLI ou ODA File Converter)
    │
    ├── → SVG (vetorial, leve, escalavel)
    ├── → HTML interativo (com pan/zoom via JS)
    └── → Thumbnail PNG (para listagem)
    │
    ▼
Armazenamento cloud (S3 / MinIO / Cloudflare R2)
    │
    ▼
Geracao de QR Code (contendo URL curta: canteiro.app/d/{qrcode_uuid})
    │
    ▼
QR Code impresso e fixado no canteiro
    │
    ▼
Qualquer dispositivo com browser escaneia → abre o SVG/HTML
```

**Ferramentas sugeridas:**
- Conversao DWG→SVG: ODA File Converter (gratuito para uso nao-comercial) ou LibreCAD CLI
- Visualizacao web: svg-pan-zoom (JS lib) ou OpenLayers para pranchas georeferenciadas
- QR Code: `qrcode` (Python lib) ou `qr-code-styling` (JS lib para QR personalizados)
- Storage: Cloudflare R2 (compativel com S3, sem egress fees)

### 5.4. Beneficio pratico no canteiro

O pedreiro escaneia o QR Code colado no pilar e ve na tela do celular:
- A planta com zoom na regiao relevante
- A versao mais recente (se houve revisao, ve a atualizada)
- Sem precisar baixar app, sem precisar de AutoCAD

---

## 6. Modulo D — Controle de Equipe

### 6.1. Objetivo

Sair do efetivo generico (12 pedreiros, 8 serventes) para um controle mais rastreavel com cadastro individual, historico de presenca e vinculo com atividades.

### 6.2. Tabelas propostas

```sql
-- Cadastro de trabalhadores (equipe propria)
trabalhadores (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    nome                VARCHAR NOT NULL,
    cpf                 VARCHAR UNIQUE,
    funcao              VARCHAR NOT NULL,       -- 'pedreiro', 'servente', 'eletricista'
    tipo                VARCHAR DEFAULT 'proprio', -- 'proprio', 'terceirizado'
    empreiteira_id      FK → empreiteiras,      -- NULL se proprio
    data_admissao       DATE,
    data_demissao       DATE,
    salario_base        DECIMAL(10,2),
    contato_telefone    VARCHAR,
    contato_emergencia  VARCHAR,
    ativo               BOOLEAN DEFAULT TRUE,
    foto_path           VARCHAR,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

-- Presenca diaria (evolucao do efetivo atual)
presenca (
    id                  SERIAL PRIMARY KEY,
    trabalhador_id      FK → trabalhadores,
    diario_id           FK → diarios_dia,
    data                DATE NOT NULL,
    presente            BOOLEAN DEFAULT TRUE,
    hora_entrada        TIME,
    hora_saida          TIME,
    horas_trabalhadas   DECIMAL(4,2),
    hora_extra          DECIMAL(4,2) DEFAULT 0,
    motivo_ausencia     VARCHAR,    -- 'falta', 'atestado', 'ferias', 'folga'
    registrado_por      FK → usuarios,
    fonte               VARCHAR DEFAULT 'rdo',  -- 'rdo', 'manual', 'ponto_eletronico'
    created_at          TIMESTAMP,
    UNIQUE(trabalhador_id, data)
);

-- Controle de EPIs
epi_entregas (
    id                  SERIAL PRIMARY KEY,
    trabalhador_id      FK → trabalhadores,
    epi_tipo            VARCHAR NOT NULL,   -- 'capacete', 'luva', 'bota', 'cinto'
    data_entrega        DATE NOT NULL,
    data_validade       DATE,
    quantidade          INTEGER DEFAULT 1,
    ca_numero           VARCHAR,            -- Certificado de Aprovacao
    assinatura_path     VARCHAR,            -- foto da ficha de EPI assinada
    registrado_por      FK → usuarios,
    created_at          TIMESTAMP
);

-- Treinamentos / integracao
treinamentos (
    id                  SERIAL PRIMARY KEY,
    trabalhador_id      FK → trabalhadores,
    tipo                VARCHAR NOT NULL,   -- 'integracao', 'nr35', 'nr18', 'nr10'
    data_realizacao     DATE,
    data_validade       DATE,
    carga_horaria       DECIMAL(4,1),
    certificado_path    VARCHAR,
    registrado_por      FK → usuarios,
    created_at          TIMESTAMP
);
```

### 6.3. Evolucao do efetivo no JSON de requisicao

O efetivo no JSON da requisicao ja foi corrigido para suportar equipe terceirizada, mas com o cadastro individual, a IA pode fazer:

```
Encarregado: "Hoje veio o Zeca, o Tonho e mais 3 serventes da Hidraulica"
    │
    ▼
IA busca: "Zeca" → Jose Carlos Silva (pedreiro, proprio)
          "Tonho" → Antonio Ferreira (pedreiro, proprio)
          "3 serventes da Hidraulica" → empreiteira "Hidraulica LTDA", funcao "servente", qtd 3
    │
    ▼
Registra presenca individual (Zeca, Tonho)
Registra efetivo generico (3 serventes terceirizados)
```

Isso preserva a praticidade (o encarregado nao precisa listar todos) mas permite rastreabilidade quando nomes sao mencionados.

---

## 7. Modulo F — Empreiteiras, Contratos e Medicoes

### 7.1. Objetivo

Cadastro formal de empreiteiras com seus contratos, escopos, valores e controle de medicoes mensais.

### 7.2. Tabelas propostas

```sql
-- Empreiteiras
empreiteiras (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR NOT NULL,
    cnpj                VARCHAR UNIQUE,
    razao_social        VARCHAR,
    contato_nome        VARCHAR,
    contato_telefone    VARCHAR,
    contato_email       VARCHAR,
    especialidade       VARCHAR,    -- 'eletrica', 'hidraulica', 'pintura', 'gesso'
    avaliacao           INTEGER,    -- 1 a 5
    ativo               BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

-- Contratos
contratos (
    id                  SERIAL PRIMARY KEY,
    obra_id             FK → obras,
    empreiteira_id      FK → empreiteiras,
    numero_contrato     VARCHAR,
    descricao_escopo    TEXT NOT NULL,
    valor_global        DECIMAL(14,2),
    tipo_contrato       VARCHAR,    -- 'preco_global', 'preco_unitario', 'administracao'
    data_inicio         DATE,
    data_termino_previsto DATE,
    data_termino_real   DATE,
    retencao_percentual DECIMAL(5,2) DEFAULT 0,   -- % retido por medicao
    status              VARCHAR DEFAULT 'ativo',   -- 'ativo', 'concluido', 'rescindido', 'suspenso'
    arquivo_contrato    VARCHAR,      -- PDF do contrato
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

-- Itens do contrato (escopo detalhado)
contrato_itens (
    id                  SERIAL PRIMARY KEY,
    contrato_id         FK → contratos,
    orcamento_item_id   FK → orcamento_itens,  -- vinculo com orcamento da obra
    descricao           TEXT,
    unidade             VARCHAR,
    quantidade          DECIMAL(12,4),
    preco_unitario      DECIMAL(12,4),
    valor_total         DECIMAL(14,2),
    created_at          TIMESTAMP
);

-- Termos aditivos
contrato_aditivos (
    id                  SERIAL PRIMARY KEY,
    contrato_id         FK → contratos,
    numero_aditivo      VARCHAR,
    tipo                VARCHAR,    -- 'acrescimo', 'supressao', 'prazo', 'reajuste'
    valor_aditivo       DECIMAL(14,2),
    novo_prazo          DATE,
    justificativa       TEXT,
    arquivo_aditivo     VARCHAR,
    aprovado_por        FK → usuarios,
    data_aprovacao      DATE,
    created_at          TIMESTAMP
);
```

### 7.3. Fluxo de medicao

```
Final do mes:
    │
    ▼
Sistema cruza:
    - Atividades executadas no periodo (via RDO) vinculadas ao contrato
    - Progresso registrado no cronograma
    │
    ▼
Gera rascunho de medicao com itens pre-preenchidos
    │
    ▼
Engenheiro revisa, ajusta quantidades, aprova
    │
    ▼
PDF de medicao gerado (WeasyPrint)
    │
    ▼
Dados alimentam:
    - Curva S financeira
    - Cronograma fisico-financeiro
    - Balancete mensal
```

---

## 8. Relation Engine v2 — Regras cruzadas entre modulos

Com todos os modulos integrados, novas regras se tornam possiveis:

### Regras novas propostas

| # | Gatilho | Acao | Modulos envolvidos |
|---|---------|------|--------------------|
| R4 | Dia improdutivo registrado | Propaga atraso no caminho critico + calcula impacto financeiro | Clima → Cronograma → Financeiro |
| R5 | Atividade concluida com atraso | Recalcula data de entrega, alerta se impacta caminho critico | RDO → Cronograma |
| R6 | NF registrada para item do orcamento | Atualiza % financeiro executado, verifica se estourou meta | Financeiro |
| R7 | NF de material pendente do cliente chega | Marca material como "recebido", libera atividade dependente | Financeiro → Materiais → Cronograma |
| R8 | Contrato de empreiteira vence em 15 dias | Alerta para o engenheiro | Contratos |
| R9 | Medicao aprovada | Atualiza curva S financeira e percentual fisico | Medicoes → Financeiro → Cronograma |
| R10 | Efetivo abaixo do minimo para atividade critica | Alerta de baixa produtividade esperada | Equipe → Cronograma |
| R11 | Documento tecnico revisado | Notifica usuarios que acessaram versao anterior | Documentos → Notificacoes |
| R12 | CPI < 0.85 por 3 competencias consecutivas | Alerta vermelho de estouro orcamentario | Financeiro |

---

## 9. Reestruturacao do banco de dados — Resumo de tabelas

### Tabelas existentes (15) — manter

```
empresas, obras, usuarios, atividades, atividade_historico,
efetivo, clima, dias_improdutivos, expediente, materiais,
equipamentos, anotacoes, fotos, diarios_dia, audit_log,
alertas, convites_acesso, solicitacoes_cadastro
```

### Tabelas novas propostas (23)

| Modulo | Tabelas | Qtd |
|--------|---------|-----|
| **Cronograma** | cronograma_tarefas, cronograma_baselines, cronograma_progresso, cronograma_desvios | 4 |
| **Financeiro** | orcamento_itens, orcamento_versoes, notas_fiscais, nf_orcamento_vinculo, fornecedores, medicoes, medicao_itens, metas_desembolso | 8 |
| **Equipe** | trabalhadores, presenca, epi_entregas, treinamentos | 4 |
| **Empreiteiras** | empreiteiras, contratos, contrato_itens, contrato_aditivos | 4 |
| **Documentos** | documentos_tecnicos, documento_revisoes, documento_atividade_vinculo, documento_acessos | 3 |

**Total projetado: 38 tabelas** (15 existentes + 23 novas)

### Diagrama de relacionamentos novos

```
cronograma_baselines
    └── cronograma_tarefas ←──── atividades (atividade_rdo_id)
            │                         │
            ├── cronograma_progresso   ├── trabalhadores (via presenca)
            │       └── diarios_dia   │       └── epi_entregas
            │                         │       └── treinamentos
            ├── cronograma_desvios    │
            │       └── dias_improdutivos
            │
            └── orcamento_itens ←──── contrato_itens
                    │                     └── contratos
                    │                           └── empreiteiras
                    │                           └── contrato_aditivos
                    ├── nf_orcamento_vinculo
                    │       └── notas_fiscais
                    │               └── fornecedores
                    │
                    └── medicao_itens
                            └── medicoes

documentos_tecnicos ←── documento_atividade_vinculo ──→ atividades
        │
        ├── documento_revisoes
        └── documento_acessos
```

---

## 10. Impacto no JSON de requisicao (exemplos_requisicoes.json)

O JSON ja foi corrigido e atualizado com os seguintes campos novos que preparam a integracao:

| Campo adicionado | Onde | Para que |
|-----------------|------|---------|
| `data_referencia` | Raiz do request | Distingue quando foi enviado de quando aconteceu |
| `obra_id` | usuario_solicitante | FK direta para a obra no banco |
| `diario_id` | Raiz do request | Vincula ao diario do dia |
| `local`, `etapa` | Cada atividade | Campos existentes na tabela atividades que faltavam |
| `percentual_concluido` | Cada atividade | Essencial para cronograma e curva S |
| `cronograma.cronograma_tarefa_id` | Cada atividade | FK para cronograma_tarefas |
| `cronograma.data_inicio/termino_previsto` | Cada atividade | Dados do baseline para comparacao |
| `cronograma.desvio_dias` | Cada atividade | Calculado automaticamente |
| `cronograma.caminho_critico` | Cada atividade | Flag do cronograma |
| `equipe.contrato_id` | Atividades terceirizadas | FK para o contrato da empreiteira |
| `efetivo.terceirizado[].contrato_id` | Efetivo | Rastreabilidade de equipe por contrato |
| `resumo_cronograma` | Bloco novo em informacoes | Snapshot de performance do dia |
| `anotacoes` como array | Bloco reestruturado | Multiplas anotacoes com tipo, prioridade e origem |

---

## 11. Roadmap de implementacao sugerido

### Fase 0 — Estabilizacao (pre-requisito)
- [ ] Finalizar WhatsApp (Evolution API)
- [ ] Resolver estado em RAM → Redis/banco
- [ ] Implementar pgvector para busca semantica de atividades
- [ ] Completar telas do painel (materiais, atividades, efetivo)

### Fase 1 — Cronograma (maior valor percebido)
- [ ] Criar tabelas cronograma_* (migration Alembic)
- [ ] Implementar importacao de Excel/CSV
- [ ] Implementar vinculo atividade RDO ↔ tarefa do cronograma
- [ ] Implementar calculo de desvios e propagacao no caminho critico
- [ ] Criar visualizacao Gantt no painel (biblioteca: Frappe Gantt ou DHTMLX Gantt)
- [ ] Criar KPIs de cronograma no dashboard
- [ ] Implementar regras R4-R5 no Relation Engine

### Fase 2 — Equipe + Empreiteiras (base para financeiro)
- [ ] Criar tabelas trabalhadores, presenca, empreiteiras, contratos
- [ ] Adaptar efetivo atual para usar tabela trabalhadores (quando disponivel)
- [ ] Cadastro de empreiteiras e contratos no painel
- [ ] Implementar regras R8, R10

### Fase 3 — Financeiro (depende de cronograma + empreiteiras)
- [ ] Criar tabelas orcamento_*, notas_fiscais, medicoes
- [ ] Implementar importacao de planilha orcamentaria
- [ ] Implementar registro de NF (manual + OCR via foto)
- [ ] Implementar curva S (fisica e financeira)
- [ ] Implementar curva ABC
- [ ] Implementar cronograma fisico-financeiro
- [ ] Gerar PDF de medicao
- [ ] Implementar regras R6, R7, R9, R12

### Fase 4 — Documentos tecnicos
- [ ] Criar tabelas documentos_tecnicos, documento_revisoes
- [ ] Implementar upload e conversao CAD → SVG
- [ ] Implementar geracao de QR Code
- [ ] Implementar viewer HTML com pan/zoom
- [ ] Implementar log de acessos
- [ ] Implementar regra R11

### Fase 5 — Inteligencia e consolidacao
- [ ] Consultas por IA ("quanto gastei esse mes?", "qual atividade mais atrasada?")
- [ ] Relatorios automaticos semanais/mensais
- [ ] API publica para integracoes externas
- [ ] Dashboard unificado do Canteiro Digital

---

## 12. Consideracoes tecnicas de infraestrutura

### Banco de dados
- **PostgreSQL** continua sendo a escolha certa. Com 38 tabelas e as queries de KPI, considere:
  - Indices compostos nas tabelas de progresso e presenca (obra_id + data)
  - Particao por obra_id nas tabelas mais volumosas (presenca, cronograma_progresso)
  - Materialized views para KPIs pesados (curva S, cronograma fisico-financeiro)

### Storage
- Para arquivos (NFs, contratos, CAD, fotos), usar **object storage** (Cloudflare R2 ou MinIO self-hosted) em vez de filesystem local
- Separar metadados (no PostgreSQL) de binarios (no object storage)

### IA
- **Whisper** para transcricao de audio (manter API OpenAI ou migrar para Whisper local)
- **Ollama/Groq** para classificacao de intencao e extracao de dados
- **pgvector** para busca semantica de atividades (resolver divida tecnica #2)
- **Pipeline de extracao de documentos** (LiteParse + LayoutLMv3 + Phi-4) para importacao de cronogramas e orcamentos nao-padronizados (conforme ja documentado em "Esqueleto Extracao project")

### VPS
- Com o crescimento de modulos, a VPS precisa comportar:
  - PostgreSQL + pgvector
  - Redis (cache de sessoes e estado)
  - MinIO ou equivalente (storage de arquivos)
  - Backend FastAPI
  - Frontend React (build estatico, pode servir via Nginx/Caddy)
  - Conversao de CAD (processo batch, nao precisa rodar 24h)
- Recomendacao: VPS com 8-16GB RAM + Groq API para IA

---

## 13. Conclusao

A transicao de **RDO Digital** para **Canteiro Digital** e uma evolucao natural e bem fundamentada. O nucleo ja existe e funciona — o que falta sao as camadas de gestao que transformam dados do dia a dia em inteligencia de obra.

A chave e manter a filosofia original: **simplicidade na entrada (audio no WhatsApp), inteligencia no processamento (IA + Relation Engine), e riqueza na saida (dashboards, KPIs, PDFs).**

Cada modulo novo nao e uma ilha — ele se conecta aos demais atraves do Relation Engine e das FKs compartilhadas (obra_id, atividade_id, cronograma_tarefa_id, orcamento_item_id). Essa malha de relacionamentos e o que transforma dados isolados em informacao acionavel.

O roadmap sugerido respeita dependencias tecnicas reais:
1. **Cronograma** primeiro — porque sem "previsto" nao existe "desvio"
2. **Equipe + Empreiteiras** depois — porque sao a base humana e contratual do financeiro
3. **Financeiro** em seguida — porque depende de cronograma (vinculo orcamento-tarefa) e empreiteiras (contratos e medicoes)
4. **Documentos** por ultimo — porque e o modulo mais independente e pode ser feito em paralelo

---

> **Proximo passo imediato:** Validar esta estrutura de tabelas com o banco existente (15 tabelas), garantir que as FKs propostas nao conflitam, e criar as primeiras migrations do modulo de cronograma.

---

*Relatorio gerado em 2026-04-11 para o projeto RDO Digital / Canteiro Digital.*
*Repositorio: https://github.com/slashline15/rdo-obra*

---

### Referências
[[Lógica por trás das decisões estratégicas|Sessão com CLAUDE para definição de estratégias de v2]]