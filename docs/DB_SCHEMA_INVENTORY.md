# Inventário de Schema do Banco

Fonte principal: `app/models.py` (schema atual carregado por SQLAlchemy).

Observação importante: o projeto ainda inicializa o banco com `Base.metadata.create_all(...)` no startup, então nem todas as tabelas-base estão cobertas por migrations versionadas. As migrations existentes cobrem apenas parte da evolução recente do schema.

## Histórico de migrations

| Revision | Arquivo | Mudanças principais |
| --- | --- | --- |
| `1b6249700f2e` | `migrations/versions/1b6249700f2e_add_clima_pluviometrico.py` | adiciona `clima.anotacao_rdo`, `clima.status_pluviometrico`, torna `clima.periodo` obrigatório e cria `uq_clima_periodo` |
| `b3cfdd8a99bb` | `migrations/versions/b3cfdd8a99bb_efetivo_tipo_expediente_obra_horarios.py` | adiciona `efetivo.tipo`, torna `efetivo.funcao` nullable, adiciona `obras.hora_inicio_padrao` e `obras.hora_termino_padrao` |
| `c9a2f8d11e44` | `migrations/versions/c9a2f8d11e44_add_usuario_admin_em_obras.py` | adiciona `obras.usuario_admin` + FK para `usuarios.id` |
| `7f3b2a1c9d10` | `migrations/versions/7f3b2a1c9d10_create_solicitacoes_cadastro.py` | cria tabela `solicitacoes_cadastro` |
| `352ace8296e0` | `migrations/versions/352ace8296e0_add_panel_foundation.py` | adiciona `usuarios.email`, `usuarios.senha_hash`; cria `diarios_dia`, `audit_log`, `alertas`; cria índices |
| `f74a0f9f9a61` | `migrations/versions/f74a0f9f9a61_access_levels_invites_soft_delete.py` | adiciona `usuarios.nivel_acesso`, `usuarios.pode_aprovar_diario`, `usuarios.registro_profissional`, `usuarios.empresa_vinculada`; adiciona soft delete em `diarios_dia`; cria `convites_acesso` |
| `8c6f0f5c2a91` | `migrations/versions/8c6f0f5c2a91_add_state_store_and_embeddings.py` | cria `conversation_states`, `atividade_embeddings`, extensão `vector` e índice `hnsw` para embeddings |

## Tabelas cobertas diretamente por migrations

- `solicitacoes_cadastro`
- `diarios_dia`
- `audit_log`
- `alertas`
- `convites_acesso`
- `conversation_states`
- `atividade_embeddings`

## Tabelas presentes no schema atual, mas não criadas nas migrations versionadas encontradas

- `empresas`
- `obras`
- `usuarios`
- `atividades`
- `atividade_historico`
- `dias_improdutivos`
- `expediente`
- `efetivo`
- `anotacoes`
- `materiais`
- `equipamentos`
- `clima`
- `fotos`

## Schema atual das tabelas

Legenda:
- `PK`: chave primária
- `Nullable`: `SIM` ou `NAO`
- `FK`: referência, quando existir

### `empresas`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| nome | VARCHAR(255) | | NAO | |
| cnpj | VARCHAR(18) | | SIM | |
| logo | VARCHAR(500) | | SIM | |
| template_pdf | VARCHAR(100) | | SIM | |
| config | JSON | | SIM | |
| created_at | DATETIME | | SIM | |

### `obras`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| nome | VARCHAR(255) | | NAO | |
| endereco | TEXT | | SIM | |
| empresa_id | INTEGER | | SIM | `empresas.id` |
| responsavel | VARCHAR(255) | | SIM | |
| data_inicio | DATE | | SIM | |
| data_fim_prevista | DATE | | SIM | |
| status | VARCHAR(20) | | SIM | |
| config | JSON | | SIM | |
| usuario_admin | INTEGER | | SIM | `usuarios.id` |
| hora_inicio_padrao | VARCHAR(5) | | SIM | |
| hora_termino_padrao | VARCHAR(5) | | SIM | |
| created_at | DATETIME | | SIM | |

### `usuarios`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| nome | VARCHAR(255) | | NAO | |
| telefone | VARCHAR(20) | | NAO | |
| obra_id | INTEGER | | SIM | `obras.id` |
| email | VARCHAR(255) | | SIM | |
| senha_hash | VARCHAR(255) | | SIM | |
| role | VARCHAR(20) | | SIM | |
| nivel_acesso | INTEGER | | NAO | |
| pode_aprovar_diario | BOOLEAN | | SIM | |
| registro_profissional | VARCHAR(255) | | SIM | |
| empresa_vinculada | VARCHAR(255) | | SIM | |
| ativo | BOOLEAN | | SIM | |
| canal_preferido | VARCHAR(20) | | SIM | |
| telegram_chat_id | VARCHAR(50) | | SIM | |
| created_at | DATETIME | | SIM | |

### `atividades`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| descricao | TEXT | | NAO | |
| local | VARCHAR(255) | | SIM | |
| etapa | VARCHAR(100) | | SIM | |
| data_inicio | DATE | | NAO | |
| data_fim_prevista | DATE | | SIM | |
| data_fim_real | DATE | | SIM | |
| status | VARCHAR(12) | | SIM | |
| percentual_concluido | FLOAT | | SIM | |
| dias_atraso | INTEGER | | SIM | |
| atividade_pai_id | INTEGER | | SIM | `atividades.id` |
| observacoes | TEXT | | SIM | |
| registrado_por | VARCHAR(255) | | SIM | |
| texto_original | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |
| updated_at | DATETIME | | SIM | |

### `atividade_historico`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| atividade_id | INTEGER | | NAO | `atividades.id` |
| data | DATE | | NAO | |
| status_anterior | VARCHAR(20) | | SIM | |
| status_novo | VARCHAR(20) | | NAO | |
| motivo | TEXT | | SIM | |
| registrado_por | VARCHAR(255) | | SIM | |
| created_at | DATETIME | | SIM | |

### `dias_improdutivos`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | NAO | |
| motivo | TEXT | | NAO | |
| clima_id | INTEGER | | SIM | `clima.id` |
| impacto | TEXT | | SIM | |
| horas_perdidas | FLOAT | | SIM | |
| created_at | DATETIME | | SIM | |

### `expediente`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | NAO | |
| hora_inicio | VARCHAR(5) | | NAO | |
| hora_termino | VARCHAR(5) | | NAO | |
| motivo | TEXT | | SIM | |
| registrado_por | VARCHAR(255) | | SIM | |
| texto_original | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |

### `efetivo`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | SIM | |
| tipo | VARCHAR(11) | | NAO | |
| funcao | VARCHAR(100) | | SIM | |
| quantidade | INTEGER | | NAO | |
| empresa | VARCHAR(255) | | SIM | |
| observacoes | TEXT | | SIM | |
| registrado_por | VARCHAR(255) | | SIM | |
| texto_original | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |

### `anotacoes`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | SIM | |
| tipo | VARCHAR(20) | | SIM | |
| descricao | TEXT | | NAO | |
| prioridade | VARCHAR(10) | | SIM | |
| resolvida | BOOLEAN | | SIM | |
| data_resolucao | DATE | | SIM | |
| atividade_id | INTEGER | | SIM | `atividades.id` |
| material_id | INTEGER | | SIM | `materiais.id` |
| auto_gerada | BOOLEAN | | SIM | |
| registrado_por | VARCHAR(255) | | SIM | |
| texto_original | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |

### `materiais`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | SIM | |
| tipo | VARCHAR(10) | | NAO | |
| material | VARCHAR(255) | | NAO | |
| quantidade | FLOAT | | SIM | |
| unidade | VARCHAR(50) | | SIM | |
| fornecedor | VARCHAR(255) | | SIM | |
| nota_fiscal | VARCHAR(100) | | SIM | |
| responsavel | VARCHAR(50) | | SIM | |
| data_prevista | DATE | | SIM | |
| observacoes | TEXT | | SIM | |
| registrado_por | VARCHAR(255) | | SIM | |
| texto_original | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |

### `equipamentos`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | SIM | |
| tipo | VARCHAR(30) | | NAO | |
| equipamento | VARCHAR(255) | | NAO | |
| quantidade | INTEGER | | SIM | |
| horas_trabalhadas | FLOAT | | SIM | |
| operador | VARCHAR(255) | | SIM | |
| observacoes | TEXT | | SIM | |
| registrado_por | VARCHAR(255) | | SIM | |
| texto_original | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |

### `clima`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | SIM | |
| periodo | VARCHAR(10) | | NAO | |
| condicao | VARCHAR(20) | | SIM | |
| anotacao_rdo | VARCHAR(5) | | SIM | |
| status_pluviometrico | VARCHAR(17) | | SIM | |
| temperatura | FLOAT | | SIM | |
| impacto_trabalho | TEXT | | SIM | |
| dia_improdutivo | BOOLEAN | | SIM | |
| observacoes | TEXT | | SIM | |
| texto_original | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |

### `fotos`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | SIM | |
| arquivo | VARCHAR(500) | | NAO | |
| descricao | TEXT | | SIM | |
| categoria | VARCHAR(50) | | SIM | |
| atividade_id | INTEGER | | SIM | `atividades.id` |
| registrado_por | VARCHAR(255) | | SIM | |
| texto_original | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |

### `conversation_states`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| channel | VARCHAR(20) | | NAO | |
| scope_key | VARCHAR(120) | | NAO | |
| state_type | VARCHAR(50) | | NAO | |
| state_token | VARCHAR(64) | | NAO | |
| payload | JSON | | NAO | |
| text_original | TEXT | | SIM | |
| source_message_id | VARCHAR(120) | | SIM | |
| expires_at | DATETIME | | NAO | |
| consumed_at | DATETIME | | SIM | |
| created_at | DATETIME | | SIM | |
| updated_at | DATETIME | | SIM | |

### `atividade_embeddings`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| atividade_id | INTEGER | | NAO | `atividades.id` |
| texto_canonico | TEXT | | NAO | |
| embedding | VECTOR(1024) | | SIM | |
| embedding_model | VARCHAR(100) | | NAO | |
| embedding_dim | INTEGER | | NAO | |
| created_at | DATETIME | | SIM | |
| updated_at | DATETIME | | SIM | |

### `solicitacoes_cadastro`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| solicitante_chat_id | VARCHAR(20) | | NAO | |
| solicitante_nome | VARCHAR(255) | | SIM | |
| solicitante_username | VARCHAR(255) | | SIM | |
| status | VARCHAR(20) | | NAO | |
| admin_decisor_id | INTEGER | | SIM | `usuarios.id` |
| observacao | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |
| updated_at | DATETIME | | SIM | |

### `diarios_dia`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | NAO | |
| status | VARCHAR(10) | | SIM | |
| submetido_por_id | INTEGER | | SIM | `usuarios.id` |
| submetido_em | DATETIME | | SIM | |
| aprovado_por_id | INTEGER | | SIM | `usuarios.id` |
| aprovado_em | DATETIME | | SIM | |
| observacao_aprovacao | TEXT | | SIM | |
| pdf_path | VARCHAR(500) | | SIM | |
| deletado_em | DATETIME | | SIM | |
| deletado_por_id | INTEGER | | SIM | `usuarios.id` |
| motivo_exclusao | TEXT | | SIM | |
| created_at | DATETIME | | SIM | |
| updated_at | DATETIME | | SIM | |

### `audit_log`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data_ref | DATE | | NAO | |
| tabela | VARCHAR(50) | | NAO | |
| registro_id | INTEGER | | NAO | |
| campo | VARCHAR(100) | | NAO | |
| valor_anterior | TEXT | | SIM | |
| valor_novo | TEXT | | SIM | |
| usuario_id | INTEGER | | NAO | `usuarios.id` |
| created_at | DATETIME | | SIM | |

### `alertas`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | NAO | `obras.id` |
| data | DATE | | NAO | |
| regra | VARCHAR(50) | | NAO | |
| severidade | VARCHAR(5) | | NAO | |
| mensagem | TEXT | | NAO | |
| resolvido | BOOLEAN | | SIM | |
| resolvido_por_id | INTEGER | | SIM | `usuarios.id` |
| resolvido_em | DATETIME | | SIM | |
| dados_contexto | JSON | | SIM | |
| created_at | DATETIME | | SIM | |

### `convites_acesso`

| Campo | Tipo | PK | Nullable | FK |
| --- | --- | --- | --- | --- |
| id | INTEGER | SIM | NAO | |
| obra_id | INTEGER | | SIM | `obras.id` |
| email | VARCHAR(255) | | NAO | |
| telefone | VARCHAR(20) | | SIM | |
| role | VARCHAR(50) | | NAO | |
| nivel_acesso | INTEGER | | NAO | |
| pode_aprovar_diario | BOOLEAN | | SIM | |
| cargo | VARCHAR(255) | | SIM | |
| token_hash | VARCHAR(64) | | NAO | |
| status | VARCHAR(20) | | NAO | |
| request_metadata | JSON | | SIM | |
| criado_por_id | INTEGER | | NAO | `usuarios.id` |
| usado_por_id | INTEGER | | SIM | `usuarios.id` |
| expira_em | DATETIME | | NAO | |
| usado_em | DATETIME | | SIM | |
| created_at | DATETIME | | SIM | |

## Constraints e observações úteis para integração

- `clima`: `UNIQUE (obra_id, data, periodo)`
- `expediente`: `UNIQUE (obra_id, data)`
- `dias_improdutivos`: `UNIQUE (obra_id, data)`
- `diarios_dia`: `UNIQUE (obra_id, data)`
- `usuarios.telefone`: único
- `usuarios.email`: único
- `convites_acesso.token_hash`: único
- `conversation_states.scope_key`: único
- `conversation_states.state_token`: único
- `atividade_embeddings.atividade_id`: único
- `atividade_embeddings.embedding`: índice HNSW por cosine no Postgres

## Referências do código

- Schema atual: `app/models.py`
- Inicialização do banco por `create_all`: `app/database.py` e `app/main.py`
- Observação anterior sobre ausência de migração completa: `docs/REVISAO_COMPLETA_MVP.md`
