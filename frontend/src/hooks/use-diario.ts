import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiFetch, apiGet, apiPost, apiPut } from "@/lib/api";

export interface PainelData {
  obra: { id: number; nome: string; endereco: string | null };
  empresa: { id: number; nome: string } | null;
  data: string;
  diario: {
    id: number;
    status: string;
    submetido_por_id: number | null;
    submetido_em: string | null;
    aprovado_por_id: number | null;
    aprovado_em: string | null;
    observacao_aprovacao: string | null;
    pdf_path: string | null;
    deletado_em: string | null;
    deletado_por_id: number | null;
    motivo_exclusao: string | null;
  };
  atividades: {
    iniciadas: Atividade[];
    em_andamento: Atividade[];
    concluidas: Atividade[];
  };
  efetivo: EfetivoItem[];
  total_efetivo: { proprio: number; empreiteiro: number; geral: number };
  clima: ClimaItem[];
  materiais: MaterialItem[];
  equipamentos: EquipamentoItem[];
  anotacoes: AnotacaoItem[];
  fotos: FotoItem[];
  expediente: Record<string, unknown> | null;
  alertas: AlertaItem[];
}

export interface Atividade {
  id: number;
  descricao: string;
  local: string | null;
  etapa: string | null;
  status: string;
  percentual_concluido: number;
  observacoes: string | null;
}

export interface EfetivoItem {
  id: number;
  funcao: string;
  quantidade: number;
  empresa: string | null;
  tipo: string | null;
  observacoes: string | null;
}

export interface ClimaItem {
  id: number;
  periodo: string | null;
  condicao: string | null;
  temperatura: number | null;
  impacto_trabalho: string | null;
}

export interface MaterialItem {
  id: number;
  tipo: string;
  material: string;
  quantidade: number | null;
  unidade: string | null;
  fornecedor: string | null;
  observacoes: string | null;
  data_prevista: string | null;
}

export interface EquipamentoItem {
  id: number;
  tipo: string;
  equipamento: string;
  quantidade: number;
  horas_trabalhadas: number | null;
  operador: string | null;
  observacoes: string | null;
}

export interface AnotacaoItem {
  id: number;
  tipo: string;
  descricao: string;
  prioridade: string;
}

export interface FotoItem {
  id: number;
  arquivo: string;
  descricao: string | null;
  categoria: string | null;
}

export interface AlertaItem {
  id: number;
  regra: string;
  severidade: string;
  mensagem: string;
  resolvido: boolean;
  dados_contexto: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogItem {
  id: number;
  tabela: string;
  registro_id: number;
  campo: string;
  valor_anterior: string | null;
  valor_novo: string | null;
  usuario_id: number;
  created_at: string;
}

export interface InviteItem {
  id: number;
  email: string;
  obra_id: number | null;
  role: string;
  nivel_acesso: number;
  pode_aprovar_diario: boolean;
  cargo: string | null;
  status: string;
  expira_em: string;
  created_at: string | null;
}

export interface DeletedDiarioItem {
  id: number;
  obra_id: number;
  data: string;
  status: string;
  pdf_path: string | null;
  deletado_em: string | null;
  deletado_por_id: number | null;
  motivo_exclusao: string | null;
}

// --- Queries ---

export function usePainel(obraId: number | null, data: string | null) {
  return useQuery({
    queryKey: ["painel", obraId, data],
    queryFn: () => apiGet<PainelData>(`/painel/${obraId}/${data}`),
    enabled: !!obraId && !!data,
  });
}

export function useObras() {
  return useQuery({
    queryKey: ["obras"],
    queryFn: () => apiGet<Array<{ id: number; nome: string; endereco: string | null }>>("/obras/"),
  });
}

export function useAuditoria(obraId: number | null, data: string | null) {
  return useQuery({
    queryKey: ["auditoria", obraId, data],
    queryFn: () => apiGet<AuditLogItem[]>(`/auditoria/${obraId}/${data}`),
    enabled: !!obraId && !!data,
  });
}

export function useConvites(obraId?: number | null, enabled = true) {
  return useQuery({
    queryKey: ["convites", obraId ?? null],
    queryFn: () =>
      apiGet<InviteItem[]>(obraId ? `/auth/invites?obra_id=${obraId}` : "/auth/invites"),
    enabled,
  });
}

export function useLixeiraDiario(
  filters: { obraId?: number | null; dataInicio?: string; dataFim?: string },
  enabled = true,
) {
  return useQuery({
    queryKey: ["diario-lixeira", filters.obraId ?? null, filters.dataInicio ?? null, filters.dataFim ?? null],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters.obraId) params.set("obra_id", String(filters.obraId));
      if (filters.dataInicio) params.set("data_inicio", filters.dataInicio);
      if (filters.dataFim) params.set("data_fim", filters.dataFim);
      return apiGet<DeletedDiarioItem[]>(`/diario/lixeira${params.size ? `?${params.toString()}` : ""}`);
    },
    enabled,
  });
}

// --- Update mutations ---

export function useUpdateEfetivo(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; [k: string]: unknown }) =>
      apiPut(`/efetivo/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useUpdateAtividade(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; [k: string]: unknown }) =>
      apiPut(`/atividades/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useUpdateMaterial(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; [k: string]: unknown }) =>
      apiPut(`/materiais/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useUpdateAnotacao(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; [k: string]: unknown }) =>
      apiPut(`/anotacoes/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

// --- Delete mutations ---

export function useDeleteEfetivo(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/efetivo/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useDeleteAtividade(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/atividades/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useDeleteMaterial(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/materiais/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useDeleteAnotacao(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete(`/anotacoes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

// --- Create mutations ---

export function useAddEfetivo(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { obra_id: number; funcao: string; quantidade: number; empresa?: string; data?: string }) =>
      apiPost(`/efetivo/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useAddAtividade(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { obra_id: number; descricao: string; local?: string; data?: string }) =>
      apiPost(`/atividades/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useAddMaterial(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { obra_id: number; tipo: string; material: string; quantidade?: number; unidade?: string; data?: string }) =>
      apiPost(`/materiais/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useAddAnotacao(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { obra_id: number; descricao: string; tipo?: string; prioridade?: string; data?: string }) =>
      apiPost(`/anotacoes/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

// --- Workflow ---

export function useTransicaoDiario(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { acao: string; observacao?: string }) =>
      apiPost(`/diario/${obraId}/${data}/transicao`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useResolverAlerta(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertaId: number) =>
      apiPut(`/alertas/${alertaId}/resolver`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
  });
}

export function useExcluirDiario(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { motivo?: string }) =>
      apiFetch(`/diario/${obraId}/${data}`, {
        method: "DELETE",
        body: JSON.stringify(body),
      }),
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
        qc.invalidateQueries({ queryKey: ["diario-lixeira", obraId] }),
        qc.invalidateQueries({ queryKey: ["auditoria", obraId, data] }),
      ]),
  });
}

export function useRestaurarDiario(obraId: number, data: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost(`/diario/${obraId}/${data}/restaurar`),
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["painel", obraId, data] }),
        qc.invalidateQueries({ queryKey: ["diario-lixeira", obraId] }),
        qc.invalidateQueries({ queryKey: ["auditoria", obraId, data] }),
      ]),
  });
}

export function useCriarConvite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      email: string;
      obra_id?: number | null;
      telefone?: string;
      role: string;
      nivel_acesso: number;
      pode_aprovar_diario?: boolean;
      cargo?: string;
    }) => apiPost<{ invite: InviteItem; token: string }>("/auth/invites", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["convites"] }),
  });
}

export function useReenviarConvite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: number) =>
      apiPost<{ invite: InviteItem; token: string }>(`/auth/invites/${inviteId}/reissue`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["convites"] }),
  });
}

export function useRevogarConvite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: number) =>
      apiPost<InviteItem>(`/auth/invites/${inviteId}/revoke`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["convites"] }),
  });
}
