import { useParams, useNavigate } from "@tanstack/react-router";
import { format, addDays, subDays, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Users,
  Cloud,
  Package,
  Wrench,
  FileText,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Camera,
  History,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import {
  usePainel,
  useTransicaoDiario,
  useResolverAlerta,
  useUpdateEfetivo,
  useUpdateAtividade,
  useUpdateMaterial,
  useUpdateAnotacao,
  useAuditoria,
  type PainelData,
  type AuditLogItem,
  type AlertaItem,
  type EfetivoItem,
  type MaterialItem,
  type AnotacaoItem,
  type ClimaItem,
  type EquipamentoItem,
  type FotoItem,
} from "@/hooks/use-diario";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

// --- Inline edit helpers ---

function EditableCell({
  value,
  onSave,
  type = "text",
  disabled,
}: {
  value: string | number | null;
  onSave: (v: string) => void;
  type?: string;
  disabled?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value ?? ""));

  if (disabled) return <span>{value ?? "—"}</span>;

  if (!editing) {
    return (
      <span
        className="cursor-pointer hover:bg-accent/50 px-1 py-0.5 rounded transition-colors"
        onClick={() => {
          setDraft(String(value ?? ""));
          setEditing(true);
        }}
      >
        {value ?? "—"}
      </span>
    );
  }

  return (
    <input
      type={type}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => {
        if (draft !== String(value ?? "")) onSave(draft);
        setEditing(false);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          if (draft !== String(value ?? "")) onSave(draft);
          setEditing(false);
        }
        if (e.key === "Escape") setEditing(false);
      }}
      className="h-7 w-full rounded border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
      autoFocus
    />
  );
}

// --- Card wrapper ---

function SectionCard({
  title,
  icon,
  count,
  children,
}: {
  title: string;
  icon: ReactNode;
  count?: number;
  children: ReactNode;
}) {
  return (
    <div className="border rounded-lg bg-card">
      <div className="flex items-center gap-2 px-4 py-3 border-b">
        {icon}
        <h3 className="font-semibold text-sm">{title}</h3>
        {count !== undefined && (
          <span className="ml-auto text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">
            {count}
          </span>
        )}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// --- Status badge ---

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  rascunho: { label: "Rascunho", color: "bg-yellow-100 text-yellow-800" },
  em_revisao: { label: "Em Revisão", color: "bg-blue-100 text-blue-800" },
  aprovado: { label: "Aprovado", color: "bg-green-100 text-green-800" },
  reaberto: { label: "Reaberto", color: "bg-orange-100 text-orange-800" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: "bg-muted text-muted-foreground" };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

// --- Alert severity badge ---

const SEVERITY_CONFIG: Record<string, { color: string; icon: ReactNode }> = {
  alta: { color: "border-red-200 bg-red-50", icon: <XCircle className="h-4 w-4 text-red-500" /> },
  media: { color: "border-yellow-200 bg-yellow-50", icon: <AlertTriangle className="h-4 w-4 text-yellow-600" /> },
  baixa: { color: "border-blue-200 bg-blue-50", icon: <Clock className="h-4 w-4 text-blue-500" /> },
};

// === Main Page ===

export default function DiarioPage() {
  const { obraId, data } = useParams({ strict: false }) as {
    obraId: string;
    data: string;
  };
  const navigate = useNavigate();
  const { isAdmin, isEngenheiro } = useAuth();

  const obraIdNum = Number(obraId);
  const { data: painel, isLoading, error } = usePainel(obraIdNum, data);

  const transicao = useTransicaoDiario(obraIdNum, data);
  const resolverAlerta = useResolverAlerta(obraIdNum, data);
  const updateEfetivo = useUpdateEfetivo(obraIdNum, data);
  const updateAtividade = useUpdateAtividade(obraIdNum, data);
  const updateMaterial = useUpdateMaterial(obraIdNum, data);
  const updateAnotacao = useUpdateAnotacao(obraIdNum, data);
  const auditoria = useAuditoria(obraIdNum, data);
  const [showAudit, setShowAudit] = useState(false);

  const isAprovado = painel?.diario.status === "aprovado";
  const canEdit = !isAprovado && isEngenheiro;

  function navDate(offset: number) {
    const newDate = format(
      offset > 0 ? addDays(parseISO(data), offset) : subDays(parseISO(data), Math.abs(offset)),
      "yyyy-MM-dd"
    );
    navigate({ to: "/obras/$obraId/diario/$data", params: { obraId, data: newDate } });
  }

  async function handleTransicao(acao: string) {
    try {
      await transicao.mutateAsync({ acao });
      toast.success(`Diário ${acao === "submeter" ? "submetido" : acao === "aprovar" ? "aprovado" : acao === "rejeitar" ? "rejeitado" : "reaberto"} com sucesso`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro na transição");
    }
  }

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        <div className="h-10 w-64 bg-muted animate-pulse rounded" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-48 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <p className="text-destructive">{error.message}</p>
      </div>
    );
  }

  if (!painel) return null;

  const alertasAtivos = painel.alertas.filter((a) => !a.resolvido);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navDate(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold">{painel.obra.nome}</h1>
            <p className="text-sm text-muted-foreground capitalize">
              {format(parseISO(data), "EEEE, dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={() => navDate(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <StatusBadge status={painel.diario.status} />
        </div>

        {/* Workflow buttons */}
        <div className="flex gap-2">
          {painel.diario.status === "rascunho" && isEngenheiro && (
            <Button size="sm" onClick={() => handleTransicao("submeter")} disabled={transicao.isPending}>
              Submeter para Revisão
            </Button>
          )}
          {painel.diario.status === "em_revisao" && isAdmin && (
            <>
              <Button size="sm" variant="outline" onClick={() => handleTransicao("rejeitar")} disabled={transicao.isPending}>
                Rejeitar
              </Button>
              <Button size="sm" onClick={() => handleTransicao("aprovar")} disabled={transicao.isPending}>
                Aprovar
              </Button>
            </>
          )}
          {painel.diario.status === "aprovado" && isAdmin && (
            <Button size="sm" variant="outline" onClick={() => handleTransicao("reabrir")} disabled={transicao.isPending}>
              Reabrir
            </Button>
          )}
          {painel.diario.status === "reaberto" && isEngenheiro && (
            <Button size="sm" onClick={() => handleTransicao("submeter")} disabled={transicao.isPending}>
              Re-submeter
            </Button>
          )}
        </div>
      </div>

      {/* Approved overlay notice */}
      {isAprovado && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          Diário aprovado — edição bloqueada.
          {painel.diario.pdf_path && (
            <a href={`/api/rdo/download/${painel.diario.pdf_path}`} className="ml-auto underline font-medium">
              Baixar PDF
            </a>
          )}
        </div>
      )}

      {/* Alerts */}
      {alertasAtivos.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            Alertas ({alertasAtivos.length})
          </h2>
          {alertasAtivos.map((alerta) => (
            <AlertCard
              key={alerta.id}
              alerta={alerta}
              onResolve={() => {
                resolverAlerta.mutate(alerta.id, {
                  onError: (e) => toast.error(e.message),
                });
              }}
            />
          ))}
        </div>
      )}

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Efetivo */}
        <SectionCard
          title="Efetivo"
          icon={<Users className="h-4 w-4 text-blue-600" />}
          count={painel.total_efetivo.geral}
        >
          <EfetivoTable items={painel.efetivo} canEdit={canEdit} onUpdate={updateEfetivo} />
        </SectionCard>

        {/* Atividades */}
        <SectionCard
          title="Atividades"
          icon={<Activity className="h-4 w-4 text-purple-600" />}
          count={
            painel.atividades.iniciadas.length +
            painel.atividades.em_andamento.length +
            painel.atividades.concluidas.length
          }
        >
          <AtividadesBlock atividades={painel.atividades} canEdit={canEdit} onUpdate={updateAtividade} />
        </SectionCard>

        {/* Clima */}
        <SectionCard
          title="Clima"
          icon={<Cloud className="h-4 w-4 text-sky-600" />}
          count={painel.clima.length}
        >
          <ClimaBlock items={painel.clima} />
        </SectionCard>

        {/* Materiais */}
        <SectionCard
          title="Materiais"
          icon={<Package className="h-4 w-4 text-amber-600" />}
          count={painel.materiais.length}
        >
          <MateriaisTable items={painel.materiais} canEdit={canEdit} onUpdate={updateMaterial} />
        </SectionCard>

        {/* Equipamentos */}
        <SectionCard
          title="Equipamentos"
          icon={<Wrench className="h-4 w-4 text-gray-600" />}
          count={painel.equipamentos.length}
        >
          <EquipamentosBlock items={painel.equipamentos} />
        </SectionCard>

        {/* Anotacoes */}
        <SectionCard
          title="Anotações"
          icon={<FileText className="h-4 w-4 text-emerald-600" />}
          count={painel.anotacoes.length}
        >
          <AnotacoesBlock items={painel.anotacoes} canEdit={canEdit} onUpdate={updateAnotacao} />
        </SectionCard>

        {/* Fotos */}
        {painel.fotos.length > 0 && (
          <SectionCard
            title="Fotos"
            icon={<Camera className="h-4 w-4 text-pink-600" />}
            count={painel.fotos.length}
          >
            <FotosBlock items={painel.fotos} />
          </SectionCard>
        )}
      </div>

      {/* Audit trail */}
      <div className="border-t pt-4">
        <Button
          variant="ghost"
          size="sm"
          className="gap-2"
          onClick={() => setShowAudit(!showAudit)}
        >
          <History className="h-4 w-4" />
          Histórico de Alterações
        </Button>

        {showAudit && (
          <div className="mt-3">
            {auditoria.isLoading ? (
              <div className="h-20 bg-muted animate-pulse rounded" />
            ) : !auditoria.data?.length ? (
              <p className="text-sm text-muted-foreground py-2">Nenhuma alteração registrada.</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {auditoria.data.map((log) => (
                  <AuditRow key={log.id} log={log} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// === Sub-components ===

function AlertCard({ alerta, onResolve }: { alerta: AlertaItem; onResolve: () => void }) {
  const cfg = SEVERITY_CONFIG[alerta.severidade] ?? SEVERITY_CONFIG.baixa;
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.color}`}>
      {cfg.icon}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{alerta.mensagem}</p>
        <p className="text-xs text-muted-foreground mt-0.5 capitalize">{alerta.regra.replace(/_/g, " ")}</p>
      </div>
      <Button size="sm" variant="ghost" className="text-xs shrink-0" onClick={onResolve}>
        Resolver
      </Button>
    </div>
  );
}

function EfetivoTable({
  items,
  canEdit,
  onUpdate,
}: {
  items: EfetivoItem[];
  canEdit: boolean;
  onUpdate: ReturnType<typeof useUpdateEfetivo>;
}) {
  if (!items.length) return <EmptyState />;

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-muted-foreground border-b">
          <th className="pb-2 font-medium">Função</th>
          <th className="pb-2 font-medium">Qtd</th>
          <th className="pb-2 font-medium">Empresa</th>
        </tr>
      </thead>
      <tbody>
        {items.map((e) => (
          <tr key={e.id} className="border-b last:border-0">
            <td className="py-2">
              <EditableCell
                value={e.funcao}
                disabled={!canEdit}
                onSave={(v) => onUpdate.mutate({ id: e.id, funcao: v })}
              />
            </td>
            <td className="py-2">
              <EditableCell
                value={e.quantidade}
                type="number"
                disabled={!canEdit}
                onSave={(v) => onUpdate.mutate({ id: e.id, quantidade: Number(v) })}
              />
            </td>
            <td className="py-2 text-muted-foreground">{e.empresa ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AtividadesBlock({
  atividades,
  canEdit,
  onUpdate,
}: {
  atividades: PainelData["atividades"];
  canEdit: boolean;
  onUpdate: ReturnType<typeof useUpdateAtividade>;
}) {
  const all = [
    ...atividades.em_andamento.map((a) => ({ ...a, _group: "Em Andamento" })),
    ...atividades.iniciadas.map((a) => ({ ...a, _group: "Iniciadas" })),
    ...atividades.concluidas.map((a) => ({ ...a, _group: "Concluídas" })),
  ];

  if (!all.length) return <EmptyState />;

  return (
    <div className="space-y-2">
      {all.map((a) => (
        <div key={a.id} className="flex items-start gap-3 py-2 border-b last:border-0">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{a.descricao}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-muted-foreground">{a._group}</span>
              {a.local && <span className="text-xs text-muted-foreground">| {a.local}</span>}
            </div>
          </div>
          <div className="text-right shrink-0">
            <EditableCell
              value={a.percentual_concluido}
              type="number"
              disabled={!canEdit}
              onSave={(v) => onUpdate.mutate({ id: a.id, percentual_concluido: Number(v) })}
            />
            <span className="text-xs text-muted-foreground">%</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function ClimaBlock({ items }: { items: ClimaItem[] }) {
  if (!items.length) return <EmptyState />;
  return (
    <div className="space-y-3">
      {items.map((c) => (
        <div key={c.id} className="flex items-center gap-4">
          <span className="text-xs font-medium uppercase text-muted-foreground w-16">
            {c.periodo ?? "—"}
          </span>
          <span className="text-sm">{c.condicao ?? "—"}</span>
          {c.temperatura != null && (
            <span className="text-sm text-muted-foreground">{c.temperatura}°C</span>
          )}
          {c.impacto_trabalho && (
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full">
              {c.impacto_trabalho}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function MateriaisTable({
  items,
  canEdit,
  onUpdate,
}: {
  items: MaterialItem[];
  canEdit: boolean;
  onUpdate: ReturnType<typeof useUpdateMaterial>;
}) {
  if (!items.length) return <EmptyState />;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-muted-foreground border-b">
          <th className="pb-2 font-medium">Material</th>
          <th className="pb-2 font-medium">Tipo</th>
          <th className="pb-2 font-medium">Qtd</th>
        </tr>
      </thead>
      <tbody>
        {items.map((m) => (
          <tr key={m.id} className="border-b last:border-0">
            <td className="py-2">{m.material}</td>
            <td className="py-2">
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  m.tipo === "entrada" ? "bg-green-100 text-green-800" : m.tipo === "pendente" ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800"
                }`}
              >
                {m.tipo}
              </span>
            </td>
            <td className="py-2">
              <EditableCell
                value={m.quantidade}
                type="number"
                disabled={!canEdit}
                onSave={(v) => onUpdate.mutate({ id: m.id, quantidade: Number(v) })}
              />
              {m.unidade && <span className="text-xs text-muted-foreground ml-1">{m.unidade}</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function EquipamentosBlock({ items }: { items: EquipamentoItem[] }) {
  if (!items.length) return <EmptyState />;
  return (
    <div className="space-y-2">
      {items.map((eq) => (
        <div key={eq.id} className="flex items-center justify-between py-2 border-b last:border-0">
          <div>
            <p className="text-sm font-medium">{eq.equipamento}</p>
            <p className="text-xs text-muted-foreground">
              {eq.tipo} | Qtd: {eq.quantidade}
              {eq.operador && ` | ${eq.operador}`}
            </p>
          </div>
          {eq.horas_trabalhadas != null && (
            <span className="text-sm text-muted-foreground">{eq.horas_trabalhadas}h</span>
          )}
        </div>
      ))}
    </div>
  );
}

function AnotacoesBlock({
  items,
  canEdit,
  onUpdate,
}: {
  items: AnotacaoItem[];
  canEdit: boolean;
  onUpdate: ReturnType<typeof useUpdateAnotacao>;
}) {
  if (!items.length) return <EmptyState />;
  return (
    <div className="space-y-2">
      {items.map((a) => (
        <div key={a.id} className="py-2 border-b last:border-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">{a.tipo}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                a.prioridade === "alta" ? "bg-red-100 text-red-800" : a.prioridade === "normal" ? "bg-gray-100 text-gray-800" : "bg-blue-100 text-blue-800"
              }`}
            >
              {a.prioridade}
            </span>
          </div>
          <EditableCell
            value={a.descricao}
            disabled={!canEdit}
            onSave={(v) => onUpdate.mutate({ id: a.id, descricao: v })}
          />
        </div>
      ))}
    </div>
  );
}

function FotosBlock({ items }: { items: FotoItem[] }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {items.map((f) => (
        <div key={f.id} className="aspect-square rounded-md bg-muted flex items-center justify-center overflow-hidden">
          <img
            src={`/api/fotos/${f.arquivo}`}
            alt={f.descricao ?? "Foto"}
            className="object-cover w-full h-full"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        </div>
      ))}
    </div>
  );
}

function AuditRow({ log }: { log: AuditLogItem }) {
  return (
    <div className="flex items-start gap-3 py-2 px-3 text-sm border rounded-md bg-muted/30">
      <div className="flex-1 min-w-0">
        <p>
          <span className="font-medium capitalize">{log.tabela}</span>
          <span className="text-muted-foreground"> #{log.registro_id} — </span>
          <span className="font-medium">{log.campo}</span>
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">
          <span className="line-through">{log.valor_anterior ?? "—"}</span>
          {" → "}
          <span className="font-medium text-foreground">{log.valor_novo ?? "—"}</span>
        </p>
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {log.created_at ? new Date(log.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : ""}
      </span>
    </div>
  );
}

function EmptyState() {
  return <p className="text-sm text-muted-foreground py-2">Nenhum registro.</p>;
}
