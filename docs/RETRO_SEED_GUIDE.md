# Seed Retroativo

## Objetivo

Popular o ambiente com histórico de obra suficiente para testar:

- dashboard
- diário por data
- fluxo de aprovação
- exportação HTML/PDF
- galeria de fotos
- alertas e pendências

O script principal é [seed_demo.py](/home/lexkaliking/.openclaw/workspace/rdo-obra/scripts/seed_demo.py).

## Comando rápido

No diretório do projeto:

```bash
cd /home/lexkaliking/.openclaw/workspace/rdo-obra
venv/bin/python -m scripts.seed_demo
```

Esse comando já cria por padrão:

- `60` dias retroativos para a obra principal
- `20` dias retroativos para a obra secundária
- atividades em vários estágios
- efetivo
- clima
- materiais
- equipamentos
- anotações
- diários em `aprovado`, `em_revisao` e `rascunho`
- fotos fake em `uploads/demo/...`

## Ajustando a quantidade de dias

Você pode aumentar ou reduzir o histórico com variáveis de ambiente:

```bash
cd /home/lexkaliking/.openclaw/workspace/rdo-obra
SEED_RETRO_DAYS=90 SEED_OBRA2_DAYS=30 venv/bin/python -m scripts.seed_demo
```

Parâmetros:

- `SEED_RETRO_DAYS`: quantidade de dias da obra principal
- `SEED_OBRA2_DAYS`: quantidade de dias da obra secundária

## Usuários criados

O seed prepara estes acessos:

- `carlos@demo.com / demo123`
- `ana@demo.com / demo123`
- `pedro@demo.com / demo123`

## O que o seed gera hoje

- obra principal com histórico operacional mais rico
- obra secundária com massa menor para comparação
- fotos demo já renderizáveis na interface e no PDF
- diários antigos aprovados para testar exportação
- dias recentes em revisão/rascunho para testar edição e workflow

## Limitações atuais

- as fotos são SVGs de demonstração, não imagens reais de obra
- o script não limpa o banco antes de rodar
- ele é pensado para enriquecer o ambiente de demo, não para fixture determinística de teste automatizado

## Próxima simplificação recomendada

O próximo passo lógico para esse seed é criar perfis prontos de carga, por exemplo:

- `demo-leve`
- `demo-comercial`
- `demo-estresse`

Assim o comando poderia virar algo como:

```bash
venv/bin/python -m scripts.seed_demo --preset demo-comercial
```

## Quando usar

- antes de revisar interface
- antes de validar exportação
- antes de gravar demo
- antes de testar regressão visual do diário
