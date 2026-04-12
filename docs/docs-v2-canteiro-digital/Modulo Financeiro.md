# Módulo Financeiro

tags: #modulos-futuros #financeiro #custos

---

## O problema que vai resolver

Saber quanto foi gasto, quando foi gasto e se está dentro do orçamento — em tempo real, sem esperar o fim do mês para fechar planilha.

---

## O que o módulo vai fazer

1. **Importar orçamento** da obra (Excel / BDI)
2. **Registrar notas fiscais** (por foto ou digitação)
3. **Gerar Curva S** automaticamente (gasto acumulado × tempo)
4. **Comparar** custo realizado × orçado por atividade/etapa
5. **Alertar** quando uma etapa está estourando o orçamento

---

## Estrutura do banco (tabelas a criar)

```sql
orcamento_itens:
  - id
  - obra_id
  - codigo_servico
  - descricao
  - quantidade
  - unidade
  - preco_unitario
  - total_previsto

notas_fiscais:
  - id
  - obra_id
  - numero
  - fornecedor
  - data_emissao
  - valor_total
  - categoria (material, servico, equipamento, outros)
  - arquivo (foto/PDF)
  - orcamento_item_id (vínculo com orçamento)
  - registrado_por

medicoes:
  - id
  - obra_id
  - competencia (mês/ano)
  - total_medido
  - percentual_avanco
  - aprovado_por
```

---

## Curva S

A Curva S mostra o gasto acumulado ao longo do tempo comparado com o planejado:

```
Valor ($)
  │     /─── realizado
  │    /  /── planejado
  │   / /
  │  / /
  │ //
  └────────── Tempo
```

Com os dados do RDO (atividades executadas) e as notas fiscais, a curva é gerada automaticamente.

---

## OCR de Notas Fiscais

Para registrar uma NF rapidamente, o encarregado tira foto da nota e manda no WhatsApp/Telegram.

O sistema usa OCR (leitura automática de texto em imagem) para extrair:
- Número da NF
- Fornecedor
- Valor
- Data

**Tecnologia:** API de visão (GPT-4o Vision ou similar)

---

## Integração com materiais

Quando uma NF for registrada para um material que foi marcado como "pendente", o sistema pode:
- Marcar automaticamente como "recebido"
- Atualizar a anotação de pendência
- Notificar o engenheiro

---

## Pré-requisito

Antes de começar este módulo:
- Módulo de Cronograma funcionando (compartilha estrutura de orçamento)
- Tela de materiais no painel completa

→ Ver [[Roadmap de Modulos]] para a ordem de implementação
→ Ver [[Modulo de Cronograma]] para o módulo anterior
