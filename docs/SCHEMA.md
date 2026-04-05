# Schema do Banco de Dados — RDO Digital

## Diagrama de relações

```
Empresa
  └── Obra (N)
        ├── Usuario (N)
        ├── Atividade (N)
        │     └── AtividadeHistorico (N)
        ├── Efetivo (N)
        ├── Expediente (N)          ← um por dia
        ├── Clima (N)               ← um por período (manhã/tarde/noite) por dia
        ├── DiaImprodutivo (N)      ← gerado pelo RelationEngine
        ├── Anotacao (N)
        ├── Material (N)
        ├── Equipamento (N)
        └── Foto (N)
```

---

## Tabelas

### `empresas`
| Campo | Tipo | Descrição |
|---|---|---|
| id | PK | |
| nome | String | |
| cnpj | String(18) | único |
| logo | String | path do arquivo |
| template_pdf | String | nome do template HTML |
| config | JSON | cores, layout, campos extras |

---

### `obras`
| Campo | Tipo | Descrição |
|---|---|---|
| id | PK | |
| nome | String | |
| endereco | Text | |
| empresa_id | FK | |
| responsavel | String | nome do engenheiro responsável |
| data_inicio | Date | |
| data_fim_prevista | Date | |
| status | String | `ativa`, `pausada`, `concluida` |
| hora_inicio_padrao | String(5) | horário padrão ex: `"07:00"` |
| hora_termino_padrao | String(5) | horário padrão ex: `"17:00"` |
| usuario_admin | FK -> usuarios.id | responsável técnico que aprova novos cadastros no bot |
| config | JSON | configurações específicas |

---

### `expediente`
Registro diário de horários. Se não houver entrada para o dia, usa os padrões da `obra`.

| Campo | Tipo | Descrição |
|---|---|---|
| id | PK | |
| obra_id | FK | |
| data | Date | |
| hora_inicio | String(5) | ex: `"07:00"` |
| hora_termino | String(5) | ex: `"19:00"` |
| motivo | Text | ex: "concretagem estendida" |
| registrado_por | String | |

**Constraint:** `UNIQUE(obra_id, data)`

**Quando criar:** só quando diferente do padrão, ou quando o usuário registrar explicitamente.

---

### `efetivo`
| Campo | Tipo | Descrição |
|---|---|---|
| id | PK | |
| obra_id | FK | |
| data | Date | |
| tipo | Enum | `proprio` \| `empreiteiro` |
| funcao | String | cargo (obrigatório para `proprio`) |
| quantidade | Integer | |
| empresa | String | obrigatório para `empreiteiro`, null para `proprio` |

**Lógica de relatório:**
- **Total empresa** = `SUM(quantidade) WHERE tipo = 'proprio'`
- **Total empreiteiras** = `SUM(quantidade) WHERE tipo = 'empreiteiro'`, agrupado por empresa
- **Total geral** = total empresa + total empreiteiras ← efetivo oficial do RDO

**Cargos padronizados (proprio):**
pedreiro, servente, carpinteiro, armador, eletricista, encanador, pintor, gesseiro, mestre, encarregado, ajudante, operador, soldador, serralheiro, vidraceiro

---

### `clima`
Um registro por **período** por **dia**. Alimenta o cabeçalho do RDO e o gráfico pluviométrico.

| Campo | Tipo | Descrição |
|---|---|---|
| id | PK | |
| obra_id | FK | |
| data | Date | |
| periodo | String(10) | `manhã` \| `tarde` \| `noite` |
| condicao | String(20) | `sol`, `nublado`, `chuva`, `chuvoso`, `tempestade` |
| anotacao_rdo | String(5) | `sol` \| `chuva` — para cabeçalho do relatório |
| status_pluviometrico | Enum | ver tabela abaixo |
| temperatura | Float | °C |
| impacto_trabalho | Text | descrição livre |
| dia_improdutivo | Boolean | flag legado (compatibilidade) |

**Constraint:** `UNIQUE(obra_id, data, periodo)`

**Padrão quando sem registro:** `seco_produtivo` (sol, tudo normal)

**Herança de período:** se manhã foi improdutiva e tarde não tem registro, sistema cria registro de tarde com o mesmo status, marcado como `[herdado da manhã — confirmar]`.

#### Status Pluviométrico

| Valor | Descrição | Cor |
|---|---|---|
| `seco_produtivo` | Sem chuva, trabalho normal | Verde `#27AE60` |
| `seco_improdutivo` | Sem chuva, mas trabalho parou (outro motivo) | Âmbar `#F39C12` |
| `chuva_produtiva` | Chuva, mas continuaram (serviços internos) | Azul `#3498DB` |
| `chuva_improdutiva` | Chuva paralisou o trabalho | Azul escuro `#1A5276` |
| `sem_expediente` | Dia sem trabalho (feriado, folga, etc.) | Cinza `#BDC3C7` |

**Regras de inferência automática:**

| Condição na mensagem | Status inferido |
|---|---|
| chuva + parou/paralisou | `chuva_improdutiva` |
| chuva + continuaram | `chuva_produtiva` |
| sem chuva + parou (TST, material, etc.) | `seco_improdutivo` |
| "sem expediente", "feriado", "folga" | `sem_expediente` |
| nenhuma menção | `seco_produtivo` (padrão) |

---

### `atividades`
| Campo | Tipo | Descrição |
|---|---|---|
| status | Enum | `iniciada`, `em_andamento`, `concluida`, `pausada`, `cancelada` |
| percentual_concluido | Float | 0–100 |
| dias_atraso | Integer | atualizado pelo RelationEngine |
| atividade_pai_id | FK self | dependência |

---

### `anotacoes`
| Campo | Tipo | Descrição |
|---|---|---|
| tipo | String | `observação`, `ocorrência`, `pendência`, `alerta`, `atraso` |
| prioridade | Enum | `baixa`, `normal`, `alta`, `urgente` |
| auto_gerada | Boolean | True = gerada pelo sistema (RelationEngine) |

---

## Migrations

Gerenciadas pelo **Alembic**.

```bash
# Ver estado atual
alembic current

# Criar nova migration após mudar models.py
alembic revision --autogenerate -m "descricao"

# Aplicar migrations
alembic upgrade head

# Reverter uma migration
alembic downgrade -1
```

Histórico:
- `1b6249700f2e` — add_clima_pluviometrico
- `b3cfdd8a99bb` — efetivo_tipo_expediente_obra_horarios
