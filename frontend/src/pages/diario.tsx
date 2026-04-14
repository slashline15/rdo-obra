import { useParams, useNavigate } from "@tanstack/react-router";
import { format, addDays, startOfMonth, subDays, parseISO } from "date-fns";
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
  Download,
  FileCode2,
  Eye,
  Pencil,
  Trash2,
  Plus,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { apiGetBlob, apiGetText, apiPost, apiPostBlob } from "@/lib/api";
import {
  usePainel,
  useObras,
  useTransicaoDiario,
  useResolverAlerta,
  useUpdateEfetivo,
  useUpdateAtividade,
  useUpdateMaterial,
  useUpdateAnotacao,
  useDeleteEfetivo,
  useDeleteAtividade,
  useDeleteMaterial,
  useDeleteAnotacao,
  useAddEfetivo,
  useAddAtividade,
  useAddMaterial,
  useAddAnotacao,
  useAuditoria,
  useExcluirDiario,
  useLixeiraDiario,
  useRestaurarDiario,
  type PainelData,
  type AuditLogItem,
  type AlertaItem,
  type DeletedDiarioItem,
  type EfetivoItem,
  type MaterialItem,
  type AnotacaoItem,
  type ClimaItem,
  type EquipamentoItem,
  type FotoItem,
  type Atividade,
} from "@/hooks/use-diario";
import { useState, useRef, type ReactNode, type FormEvent } from "react";
import { toast } from "sonner";

// --- Helpers ---

async function runMutationWithToast<T>(
  action: () => Promise<T>,
  successMessage = "Salvo com sucesso"
) {
  try {
    await action();
    toast.success(successMessage);
  } catch (err) {
    toast.error(err instanceof Error ? err.message : "Erro ao salvar");
  }
}

const inputCls =
  "h-8 rounded-md border border-input bg-background px-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground/60";

// --- Inline edit cell ---

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

  if (!editing)
    return (
      <span
        className="cursor-pointer hover:bg-accent/50 px-1 py-0.5 rounded transition-colors"
        onClick={() => { setDraft(String(value ?? "")); setEditing(true); }}
      >
        {value ?? "—"}
      </span>
    );

  return (
    <input
      type={type}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => { if (draft !== String(value ?? "")) onSave(draft); setEditing(false); }}
      onKeyDown={(e) => {
        if (e.key === "Enter") { if (draft !== String(value ?? "")) onSave(draft); setEditing(false); }
        if (e.key === "Escape") setEditing(false);
      }}
      className="h-7 w-full rounded border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
      autoFocus
    />
  );
}

// --- Section card wrapper ---

function SectionCard({ title, icon, count, children }: { title: string; icon: ReactNode; count?: number; children: ReactNode }) {
  return (
    <div className="border rounded-lg bg-card">
      <div className="flex items-center gap-2 px-4 py-3 border-b">
        {icon}
        <h3 className="font-semibold text-sm">{title}</h3>
        {count !== undefined && (
          <span className="ml-auto text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">{count}</span>
        )}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// --- Status badge ---

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  rascunho: { label: "Rascunho", color: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/25" },
  em_revisao: { label: "Em Revisão", color: "bg-sky-500/15 text-sky-400 border border-sky-500/25" },
  aprovado: { label: "Aprovado", color: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25" },
  reaberto: { label: "Reaberto", color: "bg-orange-500/15 text-orange-400 border border-orange-500/25" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: "bg-muted text-muted-foreground" };
  return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>{cfg.label}</span>;
}

// --- Alert severity config ---

const SEVERITY_CONFIG: Record<string, { color: string; icon: ReactNode }> = {
  alta: { color: "border-red-500/25 bg-red-500/10", icon: <XCircle className="h-4 w-4 text-red-400" /> },
  media: { color: "border-amber-500/25 bg-amber-500/10", icon: <AlertTriangle className="h-4 w-4 text-amber-400" /> },
  baixa: { color: "border-sky-500/25 bg-sky-500/10", icon: <Clock className="h-4 w-4 text-sky-400" /> },
};

// --- Delete row button ---

function DeleteBtn({ onDelete }: { onDelete: () => void }) {
  return (
    <button
      type="button"
      onClick={onDelete}
      className="p-1 rounded text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors shrink-0"
      title="Remover"
    >
      <Trash2 className="h-3.5 w-3.5" />
    </button>
  );
}

// ============================================================
// ADD FORMS
// ============================================================

function AddEfetivoForm({ obraId, data, onAdd }: { obraId: number; data: string; onAdd: (b: object) => Promise<unknown> }) {
  const [funcao, setFuncao] = useState("");
  const [quantidade, setQuantidade] = useState(1);
  const [empresa, setEmpresa] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!funcao.trim()) return;
    setLoading(true);
    try {
      await onAdd({ obra_id: obraId, funcao: funcao.trim(), quantidade, empresa: empresa.trim() || undefined, data });
      setFuncao(""); setQuantidade(1); setEmpresa("");
      toast.success("Efetivo adicionado");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Erro"); }
    finally { setLoading(false); }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 flex-wrap mt-3 pt-3 border-t border-dashed border-border/60">
      <input className={`${inputCls} flex-1 min-w-28`} placeholder="Função *" value={funcao} onChange={e => setFuncao(e.target.value)} required />
      <input className={`${inputCls} w-16`} type="number" min={1} placeholder="Qtd" value={quantidade} onChange={e => setQuantidade(Number(e.target.value))} />
      <input className={`${inputCls} flex-1 min-w-24`} placeholder="Empresa" value={empresa} onChange={e => setEmpresa(e.target.value)} />
      <Button type="submit" size="sm" disabled={loading} className="gap-1"><Plus className="h-3.5 w-3.5" />Add</Button>
    </form>
  );
}

function AddAtividadeForm({ obraId, data, onAdd }: { obraId: number; data: string; onAdd: (b: object) => Promise<unknown> }) {
  const [descricao, setDescricao] = useState("");
  const [local, setLocal] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!descricao.trim()) return;
    setLoading(true);
    try {
      await onAdd({ obra_id: obraId, descricao: descricao.trim(), local: local.trim() || undefined, data });
      setDescricao(""); setLocal("");
      toast.success("Atividade adicionada");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Erro"); }
    finally { setLoading(false); }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 flex-wrap mt-3 pt-3 border-t border-dashed border-border/60">
      <input className={`${inputCls} flex-1 min-w-40`} placeholder="Descrição da atividade *" value={descricao} onChange={e => setDescricao(e.target.value)} required />
      <input className={`${inputCls} flex-1 min-w-24`} placeholder="Local" value={local} onChange={e => setLocal(e.target.value)} />
      <Button type="submit" size="sm" disabled={loading} className="gap-1"><Plus className="h-3.5 w-3.5" />Add</Button>
    </form>
  );
}

function AddMaterialForm({ obraId, data, onAdd }: { obraId: number; data: string; onAdd: (b: object) => Promise<unknown> }) {
  const [material, setMaterial] = useState("");
  const [tipo, setTipo] = useState("entrada");
  const [quantidade, setQuantidade] = useState("");
  const [unidade, setUnidade] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!material.trim()) return;
    setLoading(true);
    try {
      await onAdd({
        obra_id: obraId,
        material: material.trim(),
        tipo,
        quantidade: quantidade ? Number(quantidade) : undefined,
        unidade: unidade.trim() || undefined,
        data,
      });
      setMaterial(""); setQuantidade(""); setUnidade("");
      toast.success("Material adicionado");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Erro"); }
    finally { setLoading(false); }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 flex-wrap mt-3 pt-3 border-t border-dashed border-border/60">
      <input className={`${inputCls} flex-1 min-w-36`} placeholder="Material *" value={material} onChange={e => setMaterial(e.target.value)} required />
      <select className={`${inputCls} w-28`} value={tipo} onChange={e => setTipo(e.target.value)}>
        <option value="entrada">Entrada</option>
        <option value="pendente">Pendente</option>
        <option value="falta">Falta</option>
      </select>
      <input className={`${inputCls} w-20`} type="number" placeholder="Qtd" value={quantidade} onChange={e => setQuantidade(e.target.value)} />
      <input className={`${inputCls} w-16`} placeholder="Un." value={unidade} onChange={e => setUnidade(e.target.value)} />
      <Button type="submit" size="sm" disabled={loading} className="gap-1"><Plus className="h-3.5 w-3.5" />Add</Button>
    </form>
  );
}

function AddAnotacaoForm({ obraId, data, onAdd }: { obraId: number; data: string; onAdd: (b: object) => Promise<unknown> }) {
  const [descricao, setDescricao] = useState("");
  const [tipo, setTipo] = useState("observação");
  const [prioridade, setPrioridade] = useState("normal");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!descricao.trim()) return;
    setLoading(true);
    try {
      await onAdd({ obra_id: obraId, descricao: descricao.trim(), tipo, prioridade, data });
      setDescricao("");
      toast.success("Anotação adicionada");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Erro"); }
    finally { setLoading(false); }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 flex-wrap mt-3 pt-3 border-t border-dashed border-border/60">
      <input className={`${inputCls} flex-1 min-w-48`} placeholder="Anotação *" value={descricao} onChange={e => setDescricao(e.target.value)} required />
      <select className={`${inputCls} w-28`} value={tipo} onChange={e => setTipo(e.target.value)}>
        <option value="observação">Observação</option>
        <option value="ocorrência">Ocorrência</option>
        <option value="pendência">Pendência</option>
        <option value="segurança">Segurança</option>
      </select>
      <select className={`${inputCls} w-24`} value={prioridade} onChange={e => setPrioridade(e.target.value)}>
        <option value="baixa">Baixa</option>
        <option value="normal">Normal</option>
        <option value="alta">Alta</option>
      </select>
      <Button type="submit" size="sm" disabled={loading} className="gap-1"><Plus className="h-3.5 w-3.5" />Add</Button>
    </form>
  );
}

// ============================================================
// SECTION COMPONENTS
// ============================================================

function EfetivoTable({
  items, canEdit, onUpdate, editMode, onDelete, onAdd, obraId, data,
}: {
  items: EfetivoItem[];
  canEdit: boolean;
  onUpdate: ReturnType<typeof useUpdateEfetivo>;
  editMode: boolean;
  onDelete: (id: number) => void;
  onAdd: (b: object) => Promise<unknown>;
  obraId: number;
  data: string;
}) {
  if (!items.length && !editMode) return <EmptyState />;

  return (
    <div>
      {items.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground border-b">
              <th className="pb-2 font-medium">Função</th>
              <th className="pb-2 font-medium">Qtd</th>
              <th className="pb-2 font-medium">Empresa</th>
              {editMode && <th className="pb-2 w-8" />}
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} className="border-b last:border-0 group">
                <td className="py-2">
                  <EditableCell value={e.funcao} disabled={!canEdit}
                    onSave={(v) => void runMutationWithToast(() => onUpdate.mutateAsync({ id: e.id, funcao: v }), "Salvo")} />
                </td>
                <td className="py-2 w-16">
                  <EditableCell value={e.quantidade} type="number" disabled={!canEdit}
                    onSave={(v) => void runMutationWithToast(() => onUpdate.mutateAsync({ id: e.id, quantidade: Number(v) }), "Salvo")} />
                </td>
                <td className="py-2 text-muted-foreground">{e.empresa ?? "—"}</td>
                {editMode && (
                  <td className="py-2 w-8">
                    <DeleteBtn onDelete={() => void runMutationWithToast(() => Promise.resolve(onDelete(e.id)), "Removido")} />
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!items.length && editMode && <EmptyState />}
      {editMode && <AddEfetivoForm obraId={obraId} data={data} onAdd={onAdd} />}
    </div>
  );
}

function AtividadesBlock({
  atividades, canEdit, onUpdate, editMode, onDelete, onAdd, obraId, data,
}: {
  atividades: PainelData["atividades"];
  canEdit: boolean;
  onUpdate: ReturnType<typeof useUpdateAtividade>;
  editMode: boolean;
  onDelete: (id: number) => void;
  onAdd: (b: object) => Promise<unknown>;
  obraId: number;
  data: string;
}) {
  const all: (Atividade & { _group: string })[] = [
    ...atividades.em_andamento.map((a) => ({ ...a, _group: "Em Andamento" })),
    ...atividades.iniciadas.map((a) => ({ ...a, _group: "Iniciada" })),
    ...atividades.concluidas.map((a) => ({ ...a, _group: "Concluída" })),
  ];

  const groupColor: Record<string, string> = {
    "Em Andamento": "bg-sky-500/15 text-sky-400",
    "Iniciada": "bg-amber-500/15 text-amber-400",
    "Concluída": "bg-emerald-500/15 text-emerald-400",
  };

  if (!all.length && !editMode) return <EmptyState />;

  return (
    <div>
      <div className="space-y-2">
        {all.map((a) => (
          <div key={a.id} className="flex items-start gap-3 py-2 border-b last:border-0">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">
                <EditableCell value={a.descricao} disabled={!canEdit}
                  onSave={(v) => void runMutationWithToast(() => onUpdate.mutateAsync({ id: a.id, descricao: v }), "Salvo")} />
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${groupColor[a._group] ?? "bg-muted text-muted-foreground"}`}>{a._group}</span>
                {a.local && <span className="text-xs text-muted-foreground">{a.local}</span>}
              </div>
            </div>
            <div className="text-right shrink-0 flex items-center gap-2">
              <div>
                <EditableCell value={a.percentual_concluido} type="number" disabled={!canEdit}
                  onSave={(v) => void runMutationWithToast(() => onUpdate.mutateAsync({ id: a.id, percentual_concluido: Number(v) }), "Salvo")} />
                <span className="text-xs text-muted-foreground">%</span>
              </div>
              {editMode && <DeleteBtn onDelete={() => void runMutationWithToast(() => Promise.resolve(onDelete(a.id)), "Removido")} />}
            </div>
          </div>
        ))}
      </div>
      {!all.length && editMode && <EmptyState />}
      {editMode && <AddAtividadeForm obraId={obraId} data={data} onAdd={onAdd} />}
    </div>
  );
}

function ClimaBlock({ items }: { items: ClimaItem[] }) {
  if (!items.length) return <EmptyState />;
  return (
    <div className="space-y-3">
      {items.map((c) => (
        <div key={c.id} className="flex items-center gap-4">
          <span className="text-xs font-medium uppercase text-muted-foreground w-16">{c.periodo ?? "—"}</span>
          <span className="text-sm">{c.condicao ?? "—"}</span>
          {c.temperatura != null && <span className="text-sm text-muted-foreground">{c.temperatura}°C</span>}
          {c.impacto_trabalho && (
            <span className="text-xs bg-amber-500/15 text-amber-400 px-2 py-0.5 rounded-full">{c.impacto_trabalho}</span>
          )}
        </div>
      ))}
    </div>
  );
}

function MateriaisTable({
  items, canEdit, onUpdate, editMode, onDelete, onAdd, obraId, data,
}: {
  items: MaterialItem[];
  canEdit: boolean;
  onUpdate: ReturnType<typeof useUpdateMaterial>;
  editMode: boolean;
  onDelete: (id: number) => void;
  onAdd: (b: object) => Promise<unknown>;
  obraId: number;
  data: string;
}) {
  if (!items.length && !editMode) return <EmptyState />;

  const tipoCor: Record<string, string> = {
    entrada: "bg-emerald-500/15 text-emerald-400",
    pendente: "bg-amber-500/15 text-amber-400",
    falta: "bg-red-500/15 text-red-400",
  };

  return (
    <div>
      {items.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground border-b">
              <th className="pb-2 font-medium">Material</th>
              <th className="pb-2 font-medium">Tipo</th>
              <th className="pb-2 font-medium">Qtd</th>
              {editMode && <th className="pb-2 w-8" />}
            </tr>
          </thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id} className="border-b last:border-0">
                <td className="py-2">{m.material}</td>
                <td className="py-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${tipoCor[m.tipo] ?? "bg-muted text-muted-foreground"}`}>{m.tipo}</span>
                </td>
                <td className="py-2">
                  <EditableCell value={m.quantidade} type="number" disabled={!canEdit}
                    onSave={(v) => void runMutationWithToast(() => onUpdate.mutateAsync({ id: m.id, quantidade: Number(v) }), "Salvo")} />
                  {m.unidade && <span className="text-xs text-muted-foreground ml-1">{m.unidade}</span>}
                </td>
                {editMode && (
                  <td className="py-2 w-8">
                    <DeleteBtn onDelete={() => void runMutationWithToast(() => Promise.resolve(onDelete(m.id)), "Removido")} />
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!items.length && editMode && <EmptyState />}
      {editMode && <AddMaterialForm obraId={obraId} data={data} onAdd={onAdd} />}
    </div>
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
            <p className="text-xs text-muted-foreground">{eq.tipo} | Qtd: {eq.quantidade}{eq.operador && ` | ${eq.operador}`}</p>
          </div>
          {eq.horas_trabalhadas != null && <span className="text-sm text-muted-foreground">{eq.horas_trabalhadas}h</span>}
        </div>
      ))}
    </div>
  );
}

function AnotacoesBlock({
  items, canEdit, onUpdate, editMode, onDelete, onAdd, obraId, data,
}: {
  items: AnotacaoItem[];
  canEdit: boolean;
  onUpdate: ReturnType<typeof useUpdateAnotacao>;
  editMode: boolean;
  onDelete: (id: number) => void;
  onAdd: (b: object) => Promise<unknown>;
  obraId: number;
  data: string;
}) {
  if (!items.length && !editMode) return <EmptyState />;

  return (
    <div>
      <div className="space-y-2">
        {items.map((a) => (
          <div key={a.id} className="py-2 border-b last:border-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">{a.tipo}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${a.prioridade === "alta" ? "bg-red-500/15 text-red-400" : a.prioridade === "baixa" ? "bg-sky-500/15 text-sky-400" : "bg-muted text-muted-foreground"}`}>
                {a.prioridade}
              </span>
              {editMode && (
                <span className="ml-auto">
                  <DeleteBtn onDelete={() => void runMutationWithToast(() => Promise.resolve(onDelete(a.id)), "Removido")} />
                </span>
              )}
            </div>
            <EditableCell value={a.descricao} disabled={!canEdit}
              onSave={(v) => void runMutationWithToast(() => onUpdate.mutateAsync({ id: a.id, descricao: v }), "Salvo")} />
          </div>
        ))}
      </div>
      {!items.length && editMode && <EmptyState />}
      {editMode && <AddAnotacaoForm obraId={obraId} data={data} onAdd={onAdd} />}
    </div>
  );
}

function FotosBlock({ items }: { items: FotoItem[] }) {
  // Completa com placeholders de demo (picsum) se houver menos de 4 fotos reais
  const seeds = ["construcao1", "obra2", "engineering3", "canteiro4", "civil5", "building6"];
  const placeholders: FotoItem[] = items.length < 4
    ? Array.from({ length: 4 - items.length }, (_, i) => ({
        id: -(i + 1), arquivo: "", descricao: "Foto demo", categoria: null,
      }))
    : [];
  const allItems = [...items, ...placeholders];

  return (
    <div className="grid grid-cols-3 gap-2">
      {allItems.map((f, idx) => (
        <div key={f.id} className="aspect-square rounded-md bg-muted overflow-hidden relative group">
          <img
            src={
              f.arquivo
                ? `/api/fotos/arquivo/${encodeURIComponent(f.arquivo)}`
                : `https://picsum.photos/seed/${seeds[idx % seeds.length]}/400/400`
            }
            alt={f.descricao ?? "Foto"}
            className="object-cover w-full h-full transition-transform duration-300 group-hover:scale-105"
            onError={(e) => {
              const img = e.target as HTMLImageElement;
              if (!img.src.includes("picsum")) {
                img.src = `https://picsum.photos/seed/${seeds[idx % seeds.length]}/400/400`;
              }
            }}
          />
          {f.id < 0 && (
            <div className="absolute bottom-0 inset-x-0 bg-background/60 px-2 py-1 text-[10px] text-muted-foreground backdrop-blur-sm text-center">
              demo
            </div>
          )}
          {f.descricao && f.id > 0 && (
            <div className="absolute inset-x-0 bottom-0 bg-background/75 px-2 py-1 text-[11px] text-foreground backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity">
              {f.descricao}
            </div>
          )}
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

function AlertCard({ alerta, onResolve }: { alerta: AlertaItem; onResolve: () => void }) {
  const cfg = SEVERITY_CONFIG[alerta.severidade] ?? SEVERITY_CONFIG.baixa;
  return (
    <div className={`flex items-start gap-4 p-4 rounded-2xl border ${cfg.color} backdrop-blur-sm group`}>
      <div className="mt-0.5">{cfg.icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold leading-tight">{alerta.mensagem}</p>
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mt-1">{alerta.regra.replace(/_/g, " ")}</p>
      </div>
      <Button size="sm" variant="ghost" className="h-8 px-3 text-xs font-bold uppercase tracking-wider hover:bg-background/50" onClick={onResolve}>Resolver</Button>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-10 opacity-20 select-none">
       <div className="h-10 w-10 border-2 border-dashed rounded-full flex items-center justify-center mb-3">
          <Plus className="h-5 w-5" />
       </div>
       <p className="text-xs font-bold uppercase tracking-widest">Nenhum registro</p>
    </div>
  );
}

function TimelineBlock({ items }: { items: PainelData["timeline"] }) {
  if (!items.length) return <EmptyState />;

  const typeIcon: Record<string, ReactNode> = {
    atividade: <Plus className="h-3.5 w-3.5 text-blue-400" />,
    conclusão: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
    efetivo: <Users className="h-3.5 w-3.5 text-sky-400" />,
    material: <Package className="h-3.5 w-3.5 text-amber-400" />,
    equipamento: <Wrench className="h-3.5 w-3.5 text-gray-400" />,
    anotação: <FileText className="h-3.5 w-3.5 text-emerald-400" />,
    foto: <Camera className="h-3.5 w-3.5 text-pink-400" />,
    clima: <Cloud className="h-3.5 w-3.5 text-sky-400" />,
  };

  return (
    <div className="relative space-y-4 before:absolute before:inset-y-0 before:left-[17px] before:w-[1px] before:bg-border/60">
      {items.map((item, idx) => (
        <div key={`${item.type}-${item.id}-${idx}`} className="relative pl-10 group">
          {/* Dot/Icon */}
          <div className="absolute left-0 top-1 h-[34px] w-[34px] rounded-full border bg-background flex items-center justify-center shadow-sm z-10 group-hover:border-primary/50 transition-colors">
            {typeIcon[item.type] ?? <Clock className="h-3.5 w-3.5 text-muted-foreground" />}
          </div>

          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold tracking-tight">{item.label}</span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/50">{item.author}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{item.desc}</p>
              {item.type === "foto" && item.file && (
                <div className="mt-2 h-20 w-32 rounded-lg bg-muted overflow-hidden border">
                   <img
                    src={`/api/fotos/arquivo/${encodeURIComponent(item.file)}`}
                    alt="Miniatura"
                    className="h-full w-full object-cover"
                  />
                </div>
              )}
            </div>
            <span className="text-[10px] font-mono font-medium text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded shrink-0">
              {item.ts ? format(parseISO(item.ts), "HH:mm") : "--:--"}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function SummaryGrid({ painel }: { painel: PainelData }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="rounded-2xl border bg-card/40 p-4 backdrop-blur-sm">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1">Efetivo Geral</p>
        <div className="flex items-end gap-2">
          <span className="text-2xl font-bold tracking-tight">{painel.total_efetivo.geral}</span>
          <span className="text-xs text-muted-foreground mb-1">colaboradores</span>
        </div>
      </div>
      <div className="rounded-2xl border bg-card/40 p-4 backdrop-blur-sm">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1">Atividades</p>
        <div className="flex items-end gap-2">
          <span className="text-2xl font-bold tracking-tight text-primary">{painel.atividades.concluidas.length}</span>
          <span className="text-xs text-muted-foreground mb-1">de {painel.atividades.iniciadas.length + painel.atividades.em_andamento.length + painel.atividades.concluidas.length} totais</span>
        </div>
      </div>
      <div className="rounded-2xl border bg-card/40 p-4 backdrop-blur-sm">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1">Clima Predom.</p>
        <div className="flex items-end gap-2 text-sky-400">
          <Cloud className="h-5 w-5 mb-1" />
          <span className="text-xl font-bold tracking-tight capitalize">{painel.clima[0]?.condicao ?? "—"}</span>
        </div>
      </div>
      <div className="rounded-2xl border bg-card/40 p-4 backdrop-blur-sm">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1">Alertas</p>
        <div className="flex items-end gap-2">
          <span className={`text-2xl font-bold tracking-tight ${painel.alertas.filter(a => !a.resolvido).length > 0 ? "text-amber-500" : "text-muted-foreground/30"}`}>
            {painel.alertas.filter(a => !a.resolvido).length}
          </span>
          <span className="text-xs text-muted-foreground mb-1">pendentes</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// MAIN PAGE
// ============================================================

export default function DiarioPage() {
  const { obraId, data } = useParams({ strict: false }) as { obraId: string; data: string };
  const navigate = useNavigate();
  const { isAdmin, isEngenheiro, canApproveDiario } = useAuth();

  const obraIdNum = Number(obraId);
  const { data: painel, isLoading, error } = usePainel(obraIdNum, data);
  const dateInputRef = useRef<HTMLInputElement>(null);
  const [editMode, setEditMode] = useState(false);
  const [showTrash, setShowTrash] = useState(false);
  const [rightPanel, setRightPanel] = useState<"timeline" | "audit">("timeline");
  const [trashObraId, setTrashObraId] = useState<number | null>(obraIdNum);
  const [trashStart, setTrashStart] = useState(format(startOfMonth(parseISO(data)), "yyyy-MM-dd"));
  const [trashEnd, setTrashEnd] = useState(data);

  const transicao = useTransicaoDiario(obraIdNum, data);
  const resolverAlerta = useResolverAlerta(obraIdNum, data);
  const excluirDiario = useExcluirDiario(obraIdNum, data);
  const restaurarDiario = useRestaurarDiario(obraIdNum, data);
  const updateEfetivo = useUpdateEfetivo(obraIdNum, data);
  const updateAtividade = useUpdateAtividade(obraIdNum, data);
  const updateMaterial = useUpdateMaterial(obraIdNum, data);
  const updateAnotacao = useUpdateAnotacao(obraIdNum, data);
  const deleteEfetivo = useDeleteEfetivo(obraIdNum, data);
  const deleteAtividade = useDeleteAtividade(obraIdNum, data);
  const deleteMaterial = useDeleteMaterial(obraIdNum, data);
  const deleteAnotacao = useDeleteAnotacao(obraIdNum, data);
  const addEfetivo = useAddEfetivo(obraIdNum, data);
  const addAtividade = useAddAtividade(obraIdNum, data);
  const addMaterial = useAddMaterial(obraIdNum, data);
  const addAnotacao = useAddAnotacao(obraIdNum, data);
  const auditoria = useAuditoria(obraIdNum, data);
  const { data: obras } = useObras();
  const lixeira = useLixeiraDiario({
    obraId: trashObraId,
    dataInicio: trashStart,
    dataFim: trashEnd,
  }, isAdmin && showTrash);

  const isAprovado = painel?.diario.status === "aprovado";
  const isDeleted = !!painel?.diario.deletado_em;
  const canEdit = !isAprovado && !isDeleted && isEngenheiro;

  function navDate(offset: number) {
    const newDate = format(
      offset > 0 ? addDays(parseISO(data), offset) : subDays(parseISO(data), Math.abs(offset)),
      "yyyy-MM-dd"
    );
    navigate({ to: "/obras/$obraId/diario/$data", params: { obraId, data: newDate } });
    setEditMode(false);
  }

  async function handleTransicao(acao: string) {
    try {
      await transicao.mutateAsync({ acao });
      toast.success(acao === "submeter" ? "Diário submetido" : acao === "aprovar" ? "Diário aprovado" : acao === "rejeitar" ? "Diário rejeitado" : "Diário reaberto");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro na transição");
    }
  }

  async function handlePreviewHtml() {
    try {
      const html = await apiGetText(`/rdo/preview/${obraIdNum}/${data}`);
      const w = window.open("", "_blank", "noopener,noreferrer");
      if (!w) { toast.error("Não foi possível abrir a pré-visualização"); return; }
      w.document.open(); w.document.write(html); w.document.close();
      toast.success("Pré-visualização aberta");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Erro"); }
  }

  function triggerDownload(blob: Blob, fileName: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = fileName;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  }

  async function handleExportHtml() {
    try {
      const html = await apiGetText(`/rdo/preview/${obraIdNum}/${data}`);
      triggerDownload(new Blob([html], { type: "text/html;charset=utf-8" }), `rdo-${obraIdNum}-${data}.html`);
      toast.success("HTML exportado");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Erro"); }
  }

  async function handleExportPdf() {
    try {
      const blob = await apiPostBlob("/rdo/gerar", { obra_id: obraIdNum, data, formato: "pdf" });
      triggerDownload(blob, `rdo-${obraIdNum}-${data}.pdf`);
      toast.success("PDF exportado");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Erro"); }
  }

  async function handleDownloadSavedPdf() {
    if (!painel?.diario.pdf_path) return;
    try {
      const blob = await apiGetBlob(`/rdo/download/${encodeURIComponent(painel.diario.pdf_path)}`);
      triggerDownload(blob, `rdo-${obraIdNum}-${data}.pdf`);
      toast.success("PDF baixado");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Erro"); }
  }

  async function handleDeleteDiario() {
    const motivo = window.prompt("Motivo da exclusão lógica do diário:", "Ocultado para auditoria");
    if (motivo === null) return;
    try {
      await excluirDiario.mutateAsync({ motivo: motivo.trim() || undefined });
      toast.success("Diário movido para a lixeira do admin");
      setEditMode(false);
      setShowTrash(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro");
    }
  }

  async function handleRestoreCurrentDiario() {
    try {
      await restaurarDiario.mutateAsync();
      toast.success("Diário restaurado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro");
    }
  }

  async function handleRestoreFromTrash(item: DeletedDiarioItem) {
    try {
      if (item.data === data) {
        await restaurarDiario.mutateAsync();
        toast.success("Diário restaurado");
      } else {
        await apiPost(`/diario/${item.obra_id}/${item.data}/restaurar`);
        toast.success("Diário restaurado");
        void lixeira.refetch();
        navigate({ to: "/obras/$obraId/diario/$data", params: { obraId, data: item.data } });
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro");
    }
  }

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        <div className="h-10 w-64 bg-muted animate-pulse rounded" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => <div key={i} className="h-48 bg-muted animate-pulse rounded-lg" />)}
        </div>
      </div>
    );
  }

  if (error) return <div className="p-8"><p className="text-destructive">{error.message}</p></div>;
  if (!painel) return null;

  const alertasAtivos = painel.alertas.filter((a) => !a.resolvido);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        {/* Data + navegação */}
        <div className="flex items-center gap-4">
          <div className="flex bg-card/80 border rounded-xl overflow-hidden shadow-sm backdrop-blur">
            <button
               onClick={() => navDate(-1)}
               className="p-2 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <div className="px-4 py-2 flex flex-col items-center justify-center min-w-40 border-x bg-background/5 transition-colors">
              <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{format(parseISO(data), "MMMM", { locale: ptBR })}</span>
              <span className="text-xl font-bold tracking-tighter">{format(parseISO(data), "dd")}</span>
            </div>
             <button
               onClick={() => navDate(1)}
               className="p-2 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{painel.obra.nome}</h1>
              <StatusBadge status={painel.diario.status} />
            </div>
            <div className="flex items-center gap-2">
               <p className="text-sm text-muted-foreground capitalize">
                {format(parseISO(data), "EEEE", { locale: ptBR })}
              </p>
              <div className="h-1 w-1 rounded-full bg-muted-foreground/30" />
               <button
                type="button"
                onClick={() => dateInputRef.current?.showPicker?.()}
                className="text-[11px] font-bold uppercase tracking-wider text-primary hover:underline"
              >
                Mudar data
              </button>
              <input
                ref={dateInputRef}
                type="date"
                value={data}
                onChange={(e) => {
                  if (e.target.value)
                    navigate({ to: "/obras/$obraId/diario/$data", params: { obraId, data: e.target.value } });
                }}
                className="w-0 h-0 opacity-0 absolute pointer-events-none"
                aria-hidden="true"
                tabIndex={-1}
              />
            </div>
          </div>
        </div>

        {/* Ações */}
        <div className="flex gap-2 flex-wrap items-center">
          {/* Preview buttons em grupo */}
          <div className="flex items-center bg-card border rounded-lg shadow-sm overflow-hidden mr-2">
            <button className="p-2.5 hover:bg-muted transition-colors text-muted-foreground" title="Preview" onClick={() => void handlePreviewHtml()}>
              <Eye className="h-4 w-4" />
            </button>
            <div className="w-[1px] h-4 bg-border" />
            <button className="p-2.5 hover:bg-muted transition-colors text-muted-foreground" title="HTML" onClick={() => void handleExportHtml()}>
              <FileCode2 className="h-4 w-4" />
            </button>
            <div className="w-[1px] h-4 bg-border" />
            <button className={`p-2.5 hover:bg-muted transition-colors ${!isAprovado ? "opacity-30 cursor-not-allowed" : "text-muted-foreground"}`} title="PDF" onClick={() => void handleExportPdf()} disabled={!isAprovado}>
              <Download className="h-4 w-4" />
            </button>
          </div>

          {canEdit && (
            <Button
              size="sm"
              variant={editMode ? "default" : "outline"}
              className="gap-2 rounded-lg"
              onClick={() => setEditMode(!editMode)}
            >
              {editMode ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
              {editMode ? "Fechar" : "Editar"}
            </Button>
          )}

          {painel.diario.status === "rascunho" && isEngenheiro && (
            <Button size="sm" className="rounded-lg shadow-md" onClick={() => handleTransicao("submeter")} disabled={transicao.isPending}>
              Submeter Revisão
            </Button>
          )}
          {painel.diario.status === "em_revisao" && canApproveDiario && (
            <div className="flex gap-1.5">
              <Button size="sm" variant="outline" className="rounded-lg" onClick={() => handleTransicao("rejeitar")} disabled={transicao.isPending}>Rejeitar</Button>
              <Button size="sm" className="rounded-lg shadow-md" onClick={() => handleTransicao("aprovar")} disabled={transicao.isPending}>Aprovar RDO</Button>
            </div>
          )}
          {painel.diario.status === "aprovado" && canApproveDiario && (
            <Button size="sm" variant="outline" className="rounded-lg" onClick={() => handleTransicao("reabrir")} disabled={transicao.isPending}>Reabrir</Button>
          )}

          {isAdmin && (
            <div className="flex gap-1.5 ml-2 border-l pl-3">
               {!isDeleted && (
                <button
                  onClick={() => void handleDeleteDiario()}
                  className="p-2 rounded-lg transition-colors hover:bg-red-500/10 text-muted-foreground hover:text-red-500"
                  title="Mover para lixeira"
                >
                  <Trash2 className="h-5 w-5" />
                </button>
               )}
               <button
                 onClick={() => setShowTrash(!showTrash)}
                 className={`p-2 rounded-lg transition-colors ${showTrash ? "bg-red-500/10 text-red-500" : "hover:bg-muted text-muted-foreground"}`}
                 title="Ver lixeira"
               >
                 <History className="h-5 w-5" />
               </button>
            </div>
          )}
        </div>
      </div>

      {/* Summary Row */}
      <SummaryGrid painel={painel} />

      {/* Messages / Banner */}
      <div className="space-y-3">
        {isAprovado && (
          <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400 flex items-center gap-3 backdrop-blur-sm">
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            <div className="flex-1">
              <span className="font-bold">Relatório Oficial Gerado.</span> Edição bloqueada para conformidade.
            </div>
            {painel.diario.pdf_path && (
              <Button size="sm" variant="ghost" className="gap-2 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10" onClick={() => void handleDownloadSavedPdf()}>
                <Download className="h-4 w-4" />Baixar PDF original
              </Button>
            )}
          </div>
        )}

        {isDeleted && (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300 flex items-center gap-3">
            <Trash2 className="h-5 w-5 shrink-0" />
            <div className="flex-1">Diário movido para lixeira interna. Visível apenas por administradores.</div>
            <Button size="sm" variant="outline" className="border-red-500/50 text-red-400 hover:bg-red-500/20" onClick={() => void handleRestoreCurrentDiario()}>Restaurar</Button>
          </div>
        )}

        {alertasAtivos.length > 0 && (
          <div className="space-y-2">
            {alertasAtivos.map((alerta) => (
              <AlertCard key={alerta.id} alerta={alerta}
                onResolve={() => void runMutationWithToast(() => resolverAlerta.mutateAsync(alerta.id), "Alerta resolvido")} />
            ))}
          </div>
        )}
      </div>

      {isAdmin && showTrash && (
        <SectionCard title="Lixeira Administrativa" icon={<Trash2 className="h-4 w-4 text-red-400" />} count={lixeira.data?.length}>
          {lixeira.isLoading ? (
            <div className="h-24 rounded-lg bg-muted animate-pulse" />
          ) : !lixeira.data?.length ? (
            <p className="text-sm text-muted-foreground text-center py-6">Nenhum diário removido recentemente.</p>
          ) : (
            <div className="space-y-3">
               <div className="grid gap-3 rounded-lg border bg-muted/20 p-3 md:grid-cols-[minmax(0,1fr)_170px_170px]">
                <label className="space-y-1 text-sm">
                  <span className="font-medium">Filtrar Obra</span>
                   <select className={`${inputCls} w-full`} value={trashObraId ?? ""} onChange={(e) => setTrashObraId(e.target.value ? Number(e.target.value) : null)}>
                    {obras?.map((obra) => (
                      <option key={obra.id} value={obra.id}>{obra.nome}</option>
                    ))}
                  </select>
                </label>
                 <label className="space-y-1 text-sm">
                  <span className="font-medium">Início</span>
                  <input className={inputCls} type="date" value={trashStart} onChange={(e) => setTrashStart(e.target.value)} />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="font-medium">Fim</span>
                  <input className={inputCls} type="date" value={trashEnd} onChange={(e) => setTrashEnd(e.target.value)} />
                </label>
              </div>
              {lixeira.data.map((item) => (
                <div key={item.id} className="flex items-center justify-between gap-3 rounded-xl border px-4 py-3 bg-card/40">
                  <div className="min-w-0">
                    <p className="text-sm font-bold">
                       {format(parseISO(item.data), "dd 'de' MMMM", { locale: ptBR })}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-1 italic">
                      "{item.motivo_exclusao || "Sem observação"}"
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button size="sm" variant="secondary" onClick={() => navigate({ to: "/obras/$obraId/diario/$data", params: { obraId, data: item.data } })}>
                      Ver
                    </Button>
                    <Button size="sm" onClick={() => void handleRestoreFromTrash(item)}>
                      Restaurar
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coluna Central - Detalhes (2/3 da tela) */}
        <div className="lg:col-span-2 space-y-6">
          <SectionCard title="Efetivo Diário" icon={<Users className="h-4 w-4 text-sky-400" />} count={painel.total_efetivo.geral}>
            <EfetivoTable
              items={painel.efetivo} canEdit={canEdit} onUpdate={updateEfetivo}
              editMode={editMode} obraId={obraIdNum} data={data}
              onDelete={(id) => void runMutationWithToast(() => deleteEfetivo.mutateAsync(id), "Removido")}
              onAdd={(b) => addEfetivo.mutateAsync(b as Parameters<typeof addEfetivo.mutateAsync>[0])}
            />
          </SectionCard>

          <SectionCard title="Atividades" icon={<Activity className="h-4 w-4 text-purple-400" />}
            count={painel.atividades.iniciadas.length + painel.atividades.em_andamento.length + painel.atividades.concluidas.length}>
            <AtividadesBlock
              atividades={painel.atividades} canEdit={canEdit} onUpdate={updateAtividade}
              editMode={editMode} obraId={obraIdNum} data={data}
              onDelete={(id) => void runMutationWithToast(() => deleteAtividade.mutateAsync(id), "Removido")}
              onAdd={(b) => addAtividade.mutateAsync(b as Parameters<typeof addAtividade.mutateAsync>[0])}
            />
          </SectionCard>

           <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <SectionCard title="Clima" icon={<Cloud className="h-4 w-4 text-sky-400" />} count={painel.clima.length}>
               <ClimaBlock items={painel.clima} />
             </SectionCard>
             <SectionCard title="Materiais" icon={<Package className="h-4 w-4 text-amber-400" />} count={painel.materiais.length}>
               <MateriaisTable
                 items={painel.materiais} canEdit={canEdit} onUpdate={updateMaterial}
                 editMode={editMode} obraId={obraIdNum} data={data}
                 onDelete={(id) => void runMutationWithToast(() => deleteMaterial.mutateAsync(id), "Removido")}
                 onAdd={(b) => addMaterial.mutateAsync(b as Parameters<typeof addMaterial.mutateAsync>[0])}
               />
             </SectionCard>
           </div>

           <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <SectionCard title="Equipamentos" icon={<Wrench className="h-4 w-4 text-gray-400" />} count={painel.equipamentos.length}>
               <EquipamentosBlock items={painel.equipamentos} />
             </SectionCard>
             <SectionCard title="Anotações" icon={<FileText className="h-4 w-4 text-emerald-400" />} count={painel.anotacoes.length}>
               <AnotacoesBlock
                 items={painel.anotacoes} canEdit={canEdit} onUpdate={updateAnotacao}
                 editMode={editMode} obraId={obraIdNum} data={data}
                 onDelete={(id) => void runMutationWithToast(() => deleteAnotacao.mutateAsync(id), "Removido")}
                 onAdd={(b) => addAnotacao.mutateAsync(b as Parameters<typeof addAnotacao.mutateAsync>[0])}
               />
             </SectionCard>
           </div>

          <SectionCard title="Registro Fotográfico" icon={<Camera className="h-4 w-4 text-pink-400" />} count={painel.fotos.length}>
            <FotosBlock items={painel.fotos} />
          </SectionCard>
        </div>

        {/* Coluna Direita - Timeline & Auditoria (1/3 da tela) */}
        <div className="space-y-6">
          <div className="rounded-3xl border bg-card/60 overflow-hidden shadow-sm backdrop-blur flex flex-col h-full sticky top-6 max-h-[calc(100vh-120px)]">
            <div className="flex bg-muted/30 p-1 border-b">
              <button
                onClick={() => setRightPanel("timeline")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-bold uppercase tracking-wider rounded-2xl transition-all ${rightPanel === "timeline" ? "bg-card text-primary shadow-sm" : "text-muted-foreground hover:bg-card/40"}`}
              >
                <Clock className="h-3.5 w-3.5" />
                Timeline
              </button>
              <button
                onClick={() => setRightPanel("audit")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-bold uppercase tracking-wider rounded-2xl transition-all ${rightPanel === "audit" ? "bg-card text-primary shadow-sm" : "text-muted-foreground hover:bg-card/40"}`}
              >
                <History className="h-3.5 w-3.5" />
                Auditoria
              </button>
            </div>

             <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
               {rightPanel === "timeline" ? (
                 <TimelineBlock items={painel.timeline} />
               ) : (
                  <div className="space-y-3">
                    {auditoria.isLoading ? (
                      <div className="h-24 bg-muted animate-pulse rounded-xl" />
                    ) : !auditoria.data?.length ? (
                      <div className="text-center py-20 opacity-30">
                        <History className="h-8 w-8 mx-auto mb-2" />
                        <p className="text-xs">Sem log de alterações.</p>
                      </div>
                    ) : (
                      auditoria.data.map((log) => <AuditRow key={log.id} log={log} />)
                    )}
                  </div>
               )}
             </div>

             <div className="p-4 border-t bg-muted/10">
               <div className="flex items-center justify-between text-[10px] text-muted-foreground uppercase tracking-widest font-bold">
                 <span>{rightPanel === "timeline" ? "Live Feed" : "Histórico Full"}</span>
                 <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
               </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
