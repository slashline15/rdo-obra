# Interface — Próximos Passos

## Estado atual consolidado

O painel está em estágio de **produto demonstrável**, com identidade visual definida e operação real de dados.

**Identidade visual:**
- Tema dark + laranja (baseado em engdaniel.org): background `#0a0a0a` quente, primary orange em oklch
- Tema light: branco limpo com fundo azul-frio, primário azul-aço
- Glow sutil nos cards do dark mode (`box-shadow` com traço laranja)
- Linha primária no topo do sidebar como identidade
- Toggle de tema no rodapé da sidebar

**Navegação e estrutura:**
- Sidebar expandida: Painel (Obras, Dashboard, Usuários), Planejamento (soon), Registros (soon), Configurações
- Bell de notificações com badge no header da sidebar
- Rota `/usuarios` funcional com tabela de usuários e badges de perfil
- Página de obras em grid de cards interativos (hover com lift, borda laranja, seta animada)

**Diário da obra — motor operacional completo:**
- Modo edição toggle ("Editar diário" / "Fechar edição") com banner indicativo
- **Inserção direta** pelo painel: formulários inline no final de cada seção (Efetivo, Atividades, Materiais, Anotações)
- **Remoção** por linha com botão Trash visível no modo edição
- **Edição inline** em campos de todas as seções (clique no valor)
- Seleção de data por calendário nativo (ícone CalendarDays destacado em laranja)
- Workflow de aprovação completo (rascunho → em_revisão → aprovado → reaberto)
- Exportação HTML/PDF + preview em nova aba
- Histórico de auditoria expansível
- Fotos com fallback automático para imagens Picsum (demo visual)

**API e hooks:**
- `apiDelete` adicionado em `api.ts`
- Mutations de delete para: Efetivo, Atividade, Material, Anotação
- Mutations de create para: Efetivo, Atividade, Material, Anotação
- Invalidação automática do painel após qualquer mutação

**Cores semânticas (dark/light compatíveis):**
- Alertas, insights e badges usando cores translúcidas (`/10`, `/15`, `/25`) — funciona em ambos os temas

---

## O que ainda falta

### Sprint B — Resumo e hierarquia (próxima)

- Criar uma seção `Resumo do dia` no topo do diário (% concluído, efetivo total, alertas críticos)
- Destacar bloqueios, pendências e alertas com mais clareza visual
- Separar informação principal de detalhe expandido (collapsibles)
- Tags nas atividades: local, disciplina, `data_prevista_termino`
- Clima: formulário de adição inline (igual aos outros)
- Equipamentos: formulário de adição inline

### Sprint C — Dashboard visual

- Gráfico pluviométrico (service já existe: `grafico_pluviometrico.py`)
- Gantt das atividades (Recharts ou visx)
- Sparklines nos KPI cards com tendência
- Filtro por período com date range picker

### Sprint D — RDO e exportação

- Template PDF versão **uma-folha**: colunas compactas, fontes menores, sem padding excessivo
- Separar template HTML/online do template PDF
- Assinatura digital / QR code de autenticidade

### Sprint E — Páginas "soon"

- Planejamento: cronograma Gantt de obra com marcos e fases
- Tarefas: lista de pendências cross-obra com prioridade e responsável
- Materiais: estoque consolidado por obra com alertas de ruptura
- Anotações: linha do tempo filtrada por tipo/prioridade
- Configurações: perfil de empresa, logo, template de RDO, webhooks

### Sprint F — Cara comercial

- Seed de demo robusto (30 dias de dados consistentes, fotos reais via upload)
- Roteiro de demo comercial de 10 minutos
- Onboarding Telegram corrigido (bug `user.funcao`)
- Domínio engdaniel.org configurado (backend + frontend em produção)

---

## Critério de consistência

Antes de abrir nova frente, manter esta regra:

- nenhuma área nova entra sem `consulta`
- nenhuma edição entra sem `criação`
- nenhuma exportação entra sem `estado vazio`, `erro` e `sucesso`
- nenhuma tela comercial entra sem massa de dados de demo suficiente

---

## Visão de produto

O diário precisa ser pensado como **tela de decisão**, não só tela de cadastro.

O usuário principal bate o olho e responde:
- O dia está completo?
- O que está faltando?
- O que está errado?
- Posso aprovar?
- Posso exportar?

A interface comercial vende três ideias: **controle**, **velocidade**, **confiança**.
