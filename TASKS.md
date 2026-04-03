# Tarefas — RDO Digital

## Fase 1 — MVP (prioridade máxima)

### Agent 1: Database + Core
- [ ] Setup projeto Python (FastAPI)
- [ ] Schema SQLite com todas as tabelas
- [ ] Models/ORM (SQLAlchemy ou Peewee)
- [ ] CRUD para cada entidade
- [ ] Seeds de exemplo

### Agent 2: Intent Engine (Classificação + Extração)
- [ ] Prompt engineering para classificação de intenção
- [ ] Extração de dados estruturados do texto livre
- [ ] Router de intenções (registro, consulta, correção)
- [ ] Testes com exemplos reais de obra
- [ ] Tratamento de ambiguidade (pedir confirmação)

### Agent 3: WhatsApp Gateway
- [ ] Setup Baileys ou Evolution API
- [ ] Receber mensagens de texto
- [ ] Receber áudios
- [ ] Integração com Whisper para transcrição
- [ ] Enviar respostas de confirmação
- [ ] Receber fotos com legenda

### Agent 4: Consultas + Busca Semântica
- [ ] Query builder (linguagem natural → SQL)
- [ ] Embeddings dos registros
- [ ] Busca semântica com sqlite-vss
- [ ] Respostas formatadas

### Agent 5: PDF Generator
- [ ] Template base de RDO
- [ ] Preenchimento automático com dados do dia
- [ ] Personalização por empresa (logo, cores, layout)
- [ ] Geração e envio via WhatsApp

## Fase 2 — Interface Web
- [ ] Dashboard por obra
- [ ] Timeline do dia
- [ ] Edição/correção de registros
- [ ] Aprovação pelo responsável
- [ ] Login simples (telefone + código)

## Fase 3 — Polimento
- [ ] Multi-obra
- [ ] Relatórios semanais/mensais
- [ ] Alertas (material acabando, pendências)
- [ ] API pública
- [ ] Billing (Stripe)
