# Guia do Bot — Como Registrar pelo WhatsApp/Telegram

## Fluxo de uma mensagem

```
Áudio/Texto → Transcrição (Whisper) → Classificação (Ollama) → Registro (DB) → Resposta
```

O bot usa palavras-chave primeiro (sem LLM) para casos óbvios. Quando ambíguo, guarda o estado no banco e pede uma escolha explícita:
- Telegram mostra botões inline
- WhatsApp mostra menu numerado para resposta por texto

Para conclusão de atividade, o sistema usa busca semântica com pgvector antes de confirmar o registro.

---

## O que registrar e como dizer

### Atividade (início de serviço)
> "Começamos a concretagem da laje do segundo andar"
> "Iniciamos a instalação elétrica no térreo"

### Conclusão de atividade
> "Terminamos a alvenaria do pavimento térreo"
> "Concluímos a fundação do bloco B"

### Efetivo — Empresa própria
> "Hoje temos 8 pedreiros e 4 serventes"
> "3 armadores e 2 carpinteiros presentes"

### Efetivo — Empreiteiras
> "15 funcionários da Supermix hoje"
> "Chegaram 8 da Elétrica Norte e 5 da Hidráulica Sul"

### Misto
> "Temos 6 pedreiros nossos e 12 da Supermix"

### Material
> "Chegaram 200 sacos de cimento, NF 4521"
> "Faltando 50m² de porcelanato, previsão quinta"
> "12m³ de concreto da Supermix"

### Equipamento
> "Retroescavadeira entrou hoje, 6 horas de uso"
> "Betoneira devolvida para a locadora"

### Clima
> "Sol forte a manhã toda"
> "Chuva forte de tarde, paramos tudo às 14h"
> "Choveu mas continuamos trabalhando por dentro"
> "TST do cliente parou atividade por falta de cinto" → seco_improdutivo

### Expediente (quando diferente do padrão)
> "Hoje começamos às 6h por conta da concretagem"
> "Estendemos até 19h para recuperar atraso"
> "Hoje encerramos às 16h, véspera de feriado"

### Anotação / Ocorrência
> "Vizinho reclamou de barulho, providenciar manta no tapume"
> "Pendência: renovar alvará junto à SEMMAS"
> "Visita do fiscal hoje às 10h, tudo ok"

### Foto
> Enviar foto com legenda: "Concretagem da laje — 2º pavimento"

---

## Detecção automática de período (clima)

O bot detecta o período pela mensagem:
- "manhã", "cedo", "amanhecer" → **manhã**
- "tarde", "meio-dia", "almoço" → **tarde**
- "noite", "anoitecer" → **noite**
- Sem menção → usa o horário atual (antes de 12h = manhã, 12–18h = tarde, após 18h = noite)

---

## Comportamento com confiança baixa

Se o bot não tiver certeza da categoria, apresenta um menu:

```
📋 O que você quer registrar?
1. 🏗️ Atividade
2. ✅ Conclusão
3. 👷 Efetivo
4. 📦 Material
...
```

O usuário pode responder com o número ou clicar no botão no Telegram. O estado da escolha fica salvo em PostgreSQL e espelhado em Redis para não se perder se o serviço reiniciar.

---

## Comandos especiais (Telegram)

- `/start` — vincular o chat_id ao seu usuário cadastrado

---

## Regras importantes

1. **Você não precisa ser preciso.** O bot interpreta linguagem natural.
2. **O relatório é sempre revisado antes de emitir.** A IA faz o melhor com o que recebe.
3. **Clima sem registro = dia produtivo com sol.** Só registre quando houver algo diferente.
4. **Expediente sem registro = horário padrão da obra.** Só avise quando mudar.
5. **Efetivo empreiteiro = total por empresa.** Não precisa detalhar funções.
6. **No WhatsApp, responda com texto.** Menus nativos por botão não são a base final do fluxo.
