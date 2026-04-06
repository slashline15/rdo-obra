# Interface — Próximos Passos

## Estado atual consolidado

O painel já tem base funcional para seguir evoluindo com segurança:

- autenticação e navegação entre rotas principais
- dashboard e diário integrados ao backend
- edição inline em blocos do diário
- workflow de diário (`rascunho`, `em_revisao`, `aprovado`, `reaberto`)
- exportação HTML/PDF visível na tela
- preview HTML e PDF com layout novo mais comercial
- dark mode com alternância
- seed retroativo com fotos fake

Ainda assim, o produto está numa fase em que o **motor central existe**, mas a **operação real da interface** ainda não está completa.

## Objetivo imediato

Consolidar o **motor operacional** do painel antes do refinamento visual pesado.

## O que falta hoje na interface

### Ações essenciais ausentes

- Adicionar novos registros de atividades
- Adicionar novos registros de efetivo
- Adicionar novos registros de clima
- Adicionar novos registros de materiais
- Adicionar novos registros de equipamentos
- Adicionar novas anotações
- Enviar e gerenciar fotos pela interface
- Reusar o relatório exportado como artefato histórico visível por obra/data

### Lacunas de UX operacional

- Ainda falta uma barra de ações realmente completa no topo do diário
- A página ainda mistura informação crítica com informação secundária
- Falta hierarquia clara entre “situação do dia”, “pendências”, “dados lançados” e “histórico”
- Os blocos ainda funcionam mais como leitura técnica do que como tela de decisão

### Conteúdos que precisam ser revistos

- Há informações que podem virar detalhe expansível em vez de ficarem sempre visíveis
- Falta destacar mais claramente os indicadores de decisão do responsável
- Falta separar “registro bruto” de “resumo executivo do dia”

## Proposta de ordem de execução

### Sprint A — Inclusão de dados

- Criar CTA de `Adicionar` em cada bloco do diário
- Implementar formulários rápidos, drawers ou modais curtos
- Criar estados vazios acionáveis em cada seção
- Garantir feedback consistente de loading, erro e sucesso

### Sprint B — Resumo e hierarquia

- Criar uma seção `Resumo do dia` no topo
- Destacar bloqueios, pendências e alertas com mais clareza
- Separar melhor informação principal de detalhe expandido
- Tratar o diário como tela de decisão, não só de cadastro

### Sprint C — Consolidação da exportação

- Refinar o layout PDF com fidelidade visual ao template de referência
- Revisar truncamento, densidade e ocupação de uma página
- Definir logo, assinaturas e identidade final
- Padronizar o HTML online como versão longa do relatório

### Sprint D — Cara comercial do produto

- Reforçar a identidade visual do painel
- Melhorar o dashboard como vitrine do produto
- Criar narrativa visual de “controle total da obra”
- Refinar densidade, tipografia e componentes para demo comercial

## Próximos passos lógicos

Se quisermos avançar com consistência, a ordem recomendada é:

1. Fechar inserção de novos dados no diário.
2. Organizar o topo do diário com resumo, pendências e ações principais.
3. Refinar o relatório exportado até ele virar artefato comercial.
4. Só então fazer polimento visual mais amplo do restante da interface.

## Critério de consistência

Antes de abrir uma nova frente de UI, vale manter esta regra:

- nenhuma área nova entra sem `consulta`
- nenhuma edição entra sem `criação`
- nenhuma exportação entra sem `estado vazio`, `erro` e `sucesso`
- nenhuma tela comercial entra sem massa de dados de demo suficiente

## Recomendações de produto

- O diário precisa ser pensado como **tela de decisão**, não só tela de cadastro.
- O usuário principal precisa bater o olho e responder rapidamente:
  - O dia está completo?
  - O que está faltando?
  - O que está errado?
  - Posso aprovar?
  - Posso exportar?

- A interface comercial depois deve vender três ideias:
  - controle
  - velocidade
  - confiança
