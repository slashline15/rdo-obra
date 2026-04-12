# Módulo de Cronograma

tags: #modulos-futuros #cronograma #planejamento

---

## O problema que vai resolver

Hoje o sistema sabe o que foi feito (via RDO), mas não sabe o que *deveria ter sido feito*. Sem isso, não tem como saber se a obra está no prazo.

O módulo de cronograma vai conectar o **planejado** com o **executado**.

---

## O que o módulo vai fazer

1. **Importar o cronograma** da obra (Excel ou MS Project)
2. **Vincular tarefas do cronograma** às atividades do RDO
3. **Calcular automaticamente** se está adiantado, no prazo ou atrasado
4. **Gerar gráfico Previsto × Realizado** no dashboard
5. **Alertar** quando uma atividade crítica está em risco

---

## Fontes de cronograma suportadas (planejadas)

| Formato | Ferramenta | Como importar |
|---------|-----------|---------------|
| `.xlsx` / `.xls` | Excel / LibreOffice | Upload de arquivo pelo painel |
| `.mpp` | MS Project | Upload de arquivo pelo painel |
| `.csv` | Qualquer planilha | Upload de arquivo pelo painel |
| `.json` | Primavera P6 (exportação) | Upload de arquivo pelo painel |

---

## Estrutura do banco (tabelas a criar)

```sql
cronograma_tarefas:
  - id
  - obra_id
  - nome
  - data_inicio_prevista
  - data_fim_prevista
  - duracao_dias
  - responsavel
  - predecessora_id (dependência)
  - caminho_critico (boolean)
  - atividade_rdo_id (vínculo com atividade registrada)

cronograma_baseline:
  - id
  - obra_id
  - versao (v1, v2...)
  - data_import
  - arquivo_original
  - dados_json (snapshot do cronograma)
```

---

## Como vai funcionar no dia a dia

```
Engenheiro importa cronograma no início da obra
  ↓
Sistema cria as tarefas do cronograma no banco
  ↓
Ao longo do tempo, atividades do RDO são vinculadas às tarefas
  (manual: engenheiro vincula / ou automático: IA sugere vínculo por nome)
  ↓
Dashboard mostra:
  → "Concretagem do 3° andar: previsto para 10/04, registrado como iniciado em 12/04 — 2 dias atrasado"
  → Gráfico de Gantt simplificado
  → Curva de progresso (% realizado × % previsto)
```

---

## Desafio técnico principal

**Importar MS Project (.mpp):** Formato proprietário da Microsoft, difícil de ler diretamente.

**Solução sugerida:**
1. Pedir que o engenheiro exporte como XML do MS Project (opção nativa)
2. Ou exportar para Excel antes de fazer upload
3. Biblioteca Python `python-pptx` ou `mpxj` podem ajudar

---

## Integração com o Relation Engine

Quando o módulo estiver pronto, novas regras automáticas se tornam possíveis:

- Dia improdutivo → atraso propagado no caminho crítico
- Atividade concluída com atraso → alerta de impacto no prazo de entrega
- Material pendente + atividade crítica → alerta vermelho para o engenheiro

---

## Pré-requisito

Antes de começar este módulo:
- Painel web com telas de atividades completas
- WhatsApp funcionando
- Base de dados populada com dados reais de teste

→ Ver [[Roadmap de Modulos]] para a ordem de implementação
