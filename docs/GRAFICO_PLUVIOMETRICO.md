# Gráfico Pluviométrico — Disco Mensal

## Conceito

Disco circular que representa visualmente a produtividade climática de cada dia do mês de obra. Permite identificar padrões de chuva e improdutividade de forma imediata no relatório.

## Estrutura Visual

```
         Dia 1
        /
   [manhã]     ← anel externo
   [tarde]     ← anel médio
   [noite]     ← anel interno
        \
         Dia 2 ...
```

- **31 fatias** — uma por dia do mês (independente de quantos dias o mês tem)
- **3 anéis** por fatia — de fora para dentro: manhã, tarde, noite
- Sentido horário, começando do topo (dia 1)
- Dias futuros ficam em cinza claro

## Paleta de Cores

| Status | Cor | Hex |
|---|---|---|
| Seco produtivo | Verde | `#27AE60` |
| Seco improdutivo | Âmbar | `#F39C12` |
| Chuva produtiva | Azul | `#3498DB` |
| Chuva improdutiva | Azul escuro | `#1A5276` |
| Sem expediente | Cinza | `#BDC3C7` |
| Dia futuro / sem dado | Cinza claro | `#ECF0F1` |

## Uso no Código

```python
from app.services.grafico_pluviometrico import gerar_disco_mensal, status_do_mes
from app.database import SessionLocal

db = SessionLocal()

# Gerar SVG
svg = gerar_disco_mensal(obra_id=1, ano=2026, mes=4, db=db)
with open("output/disco_abril.svg", "w") as f:
    f.write(svg)

# Estatísticas para o relatório
stats = status_do_mes(obra_id=1, ano=2026, mes=4, db=db)
# {
#   "total_dias": 30,
#   "seco_produtivo": 18,
#   "seco_improdutivo": 2,
#   "chuva_produtiva": 5,
#   "chuva_improdutiva": 3,
#   "sem_expediente": 2,
#   "dias_chuva": 8,
#   "dias_improdutivos": 5,
# }
```

## Parâmetros

`gerar_disco_mensal(obra_id, ano, mes, db, largura=640, altura=640)`

- `obra_id` — ID da obra no banco
- `ano`, `mes` — mês de referência
- `db` — sessão SQLAlchemy
- `largura`, `altura` — dimensões do SVG em pixels (padrão 640×640)

## Integração com o RDO

O disco é embutido no PDF do RDO como imagem SVG inline. Para incluir:

```python
# No template Jinja2 do RDO
{{ disco_svg | safe }}
```

O módulo `rdo_generator.py` deve chamar `gerar_disco_mensal()` e passar o resultado para o contexto do template.

## Lógica de Dados

- Busca todos os registros `Clima` do mês filtrados por `obra_id`
- Indexa por `(dia, periodo)`
- Dias sem registro → `seco_produtivo` (verde, padrão)
- Dias futuros → cinza claro (sem cor de status)

## Regras de Negócio

1. **O usuário não precisa registrar clima todos os dias.** Silêncio = sol + produtivo.
2. **Terceiro turno (noite) raramente usado.** Aparece no disco mas raramente preenchido.
3. **Herança automática:** se manhã foi improdutiva e tarde não tem registro, o sistema preenche tarde com o mesmo status.
4. **O disco é para visualização e relatório.** A IA usa o que recebe; o usuário revisa manualmente antes de emitir o RDO.
