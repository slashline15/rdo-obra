# Plano de Execução

> **Objetivo geral**: transformar o painel de controle de obra em um produto vendável pronto para aprovação **antes da entrega**.  
> Enfatizamos três pilares: **controle**, **modernidade** e **inteligência** já na primeira impressão.

| Pilar         | O que buscamos                                 |
|---------------|-----------------------------------------------|
| Controle      | Cliente sente domínio completo: “eu controlo a obra daqui”. |
| Modernidade   | Interface responsiva, design clean, componentes reutilizáveis. |
| Inteligência | Regras automatizadas de alerta e insights gerando valor imediato. |

---

## Visão geral do fluxo principal

1. **Abrir o dia da obra**  
2. **Ver o que o bot registrou** (com confiança/alertas)  
3. **Corrigir rapidamente** (inline + modal)  
4. **Aprovar o diário** (workflow de status)  
5. **Gerar/baixar PDF** (apenas após aprovação)

---

## Sprint Backlog Estruturado

> **Temporização**  
> 4 sprints, 1 semana/apartir do Sprint 1, Sprint 0 (4–5 dias).  

| Sprint | Dados | Objetivo | Principais Ticket |
|-------|-------|----------|-------------------|
| **0 – Descoberta + Wireframes** | 4‑5 dias | Travar escopo e UI antes do desenvolvimento | S0‑T1, S0‑T2, S0‑T3 |
| **1 – MVP do painel de revisão** | 1 semana | Disponibilizar a revisão diária funcional | S1‑T1, S1‑T2, S1‑T3 |
| **2 – Aprovação + Auditoria** | 1 semana | Formalizar processo de aprovação confiável | S2‑T1, S2‑T2, S2‑T3 |
| **3 – Dashboard executivo** | 1 semana | Criar a “cara comercial” do produto | S3‑T1, S3‑T2, S3‑T3 |

---

## Detalhamento dos Tickets

### Sprint 0 – Descoberta + Especificação

| Ticket | Descrição | Critérios de Aceite |
|--------|-----------|---------------------|
| **S0‑T1** | Especificação funcional da tela “Revisão diária” | 1. Fluxo “abrir dia → revisar → aprovar → gerar PDF”.<br>2. Campos obrigatórios/opcionais definidos.<br>3. Regras de bloqueio (p.ex. sem efetivo).<br>4. Aprovação do stakeholder. |
| **S0‑T2** | Wireframe funcional (baixa/média fidelidade) | 1. Navegação completa com 1 fluxo principal.<br>2. Estados: “dados incompletos”, “dados com alerta”.<br>3. Loading/erro mapeados.<br>4. Feedback aprovado. |
| **S0‑T3** | Design System inicial (controle + modernidade) | 1. Paleta, tipografia e espaçamento definidos.<br>2. 6 componentes base (Cards, Tabela inteligente, Badges, Timeline).<br>3. Identidade visual aprovada. |

---

### Sprint 1 – MVP do Painel de Revisão

| Ticket | Descrição | Critérios de Aceite |
|--------|-----------|---------------------|
| **S1‑T1** | Página “Diário da Obra” | 1. Exibir blocos consolidados (atividades, efetivo, clima, materiais, anotações, fotos).<br>2. Totais principais visíveis.<br>3. Filtro por obra + data funcional. |
| **S1‑T2** | Edição rápida inline | 1. 4 tipos de registro editáveis inline.<br>2. Estado da página atualiza sem recarga.<br>3. Toast padrão de sucesso/erro. |
| **S1‑T3** | Painel de “alertas inteligentes” | 1. 5 regras de alerta implementadas.<br>2. Severidades (alto/médio/baixo).<br>3. Ação “resolver alerta” dentro da tela. |

---

### Sprint 2 – Aprovação Oficial & Trilha de Auditoria

| Ticket | Descrição | Critérios de Aceite |
|--------|-----------|---------------------|
| **S2‑T1** | Workflow de status do diário | 1. Transições rascunho → em_revisão → aprovado → reaberto.<br>2. Registro de usuário/data/hora.<br>3. Restringir aprovação a perfis autorizados.<br>4. Diário “travado” após aprovação. |
| **S2‑T2** | Auditoria de alterações | 1. Log de mudanças (campo, antigo, novo, autor, timestamp).<br>2. Histórico visual por diário.<br>3. Exportação em JSON.<br>4. Cobertura de 4 entidades. |
| **S2‑T3** | Geração PDF pós-aprovação | 1. Botão disponível apenas com status aprovado.<br>2. Download funcional.<br>3. Mensagem de erro em falta de dependências. |

---

### Sprint 3 – Dashboard Executivo

| Ticket | Descrição | Critérios de Aceite |
|--------|-----------|---------------------|
| **S3‑T1** | Dashboard executivo | 1. 6 KPIs em cards (produtividade, dias improdutivos, retrabalho, tempo médio até aprovação, etc.).<br>2. Filtros por obra/intervalo.<br>3. Performance < 2 s para período mensal. |
| **S3‑T2** | “Inteligência visível” | 1. Insights em linguagem simples (ex.: "3 dias improdutivos por chuva").<br>2. Evidência de cálculo rastreável.<br>3. Sem “alucinação” – com dado real. |
| **S3‑T3** | Pronto para demo comercial | 1. Roteiro de 10 minutos com foco em valor de negócio.<br>2. Base de dados demo consistente.<br>3. Storyline “controle total da obra” validada. |

---

## Requisitos Transversais (em paralelo)

| RQ | Descrição |
|----|------------|
| **RQ‑1 – Segurança mínima** | Autenticação e autorização por perfil. Evita bloqueios de escala. |
| **RQ‑2 – Observabilidade** | Logs críticos: edição, aprovação, geração de PDF. |
| **RQ‑3 – Testes** | Suite mínima por sprint (integração do fluxo principal + regressão de aprovação). |

---

## Definição de Pronto (DoD) por Ticket

* Critérios de aceite atendidos.  
* Teste manual do fluxo principal.  
* Teste automatizado (quando aplicável).  
* Sem regressão no fluxo de bot.  
* Documentação curta de uso.  

---

## Próximos passos

1. **Especificação funcional da tela de revisão** (campos + ações + regras)
2. **Wireframe textual detalhado por seção**
3. **Primeira lista de endpoints necessários para o frontend** 

---

> **Mensagem final**: Este plano está pronto para o que chama de “controle total da obra”, dedicação à modernidade e inteligência. Vamos transformar a visão em realidade!