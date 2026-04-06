import { useParams, useNavigate } from "@tanstack/react-router";
import { format, addDays, subDays, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  ChevronLeft,
  ChevronRight,
  CalendarDays,
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
import { apiGetBlob, apiGetText, apiPostBlob } from "@/lib/api";
import {
  usePainel,
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
  type PainelData,
  type AuditLogItem,
  type AlertaItem,
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
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.color}`}>
      {cfg.icon}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{alerta.mensagem}</p>
        <p className="text-xs text-muted-foreground mt-0.5 capitalize">{alerta.regra.replace(/_/g, " ")}</p>
      </div>
      <Button size="sm" variant="ghost" className="text-xs shrink-0" onClick={onResolve}>Resolver</Button>
    </div>
  );
}

function EmptyState() {
  return <p className="text-sm text-muted-foreground py-2">Nenhum registro.</p>;
}

// ============================================================
// MAIN PAGE
// ============================================================

export default function DiarioPage() {
  const { obraId, data } = useParams({ strict: false }) as { obraId: string; data: string };
  const navigate = useNavigate();
  const { isAdmin, isEngenheiro } = useAuth();

  const obraIdNum = Number(obraId);
  const { data: painel, isLoading, error } = usePainel(obraIdNum, data);
  const dateInputRef = useRef<HTMLInputElement>(null);
  const [editMode, setEditMode] = useState(false);
  const [showAudit, setShowAudit] = useState(false);

  const transicao = useTransicaoDiario(obraIdNum, data);
  const resolverAlerta = useResolverAlerta(obraIdNum, data);
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

  const isAprovado = painel?.diario.status === "aprovado";
  const canEdit = !isAprovado && isEngenheiro;

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
      <div className="flex items-start justify-between flex-wrap gap-4">
        {/* Data + navegação */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => navDate(-1)} className="shrink-0">
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <div>
            <h1 className="text-xl font-bold">{painel.obra.nome}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-sm text-muted-foreground capitalize">
                {format(parseISO(data), "EEEE, dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
              </p>
              {/* Calendar picker — ícone grande e chamativo */}
              <button
                type="button"
                onClick={() => dateInputRef.current?.showPicker?.()}
                className="flex items-center justify-center h-7 w-7 rounded-lg bg-primary/15 border border-primary/25 text-primary hover:bg-primary/25 hover:border-primary/50 hover:scale-105 transition-all"
                title="Escolher data"
              >
                <CalendarDays className="h-4 w-4" />
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

          <Button variant="ghost" size="icon" onClick={() => navDate(1)} className="shrink-0">
            <ChevronRight className="h-4 w-4" />
          </Button>

          <StatusBadge status={painel.diario.status} />
        </div>

        {/* Ações */}
        <div className="flex gap-2 flex-wrap justify-end">
          {/* Modo edição — botão principal */}
          {canEdit && (
            <Button
              size="sm"
              variant={editMode ? "default" : "outline"}
              className={`gap-2 ${editMode ? "border-primary" : ""}`}
              onClick={() => setEditMode(!editMode)}
            >
              {editMode ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
              {editMode ? "Fechar edição" : "Editar diário"}
            </Button>
          )}

          <Button size="sm" variant="outline" className="gap-2" onClick={() => void handlePreviewHtml()}>
            <Eye className="h-4 w-4" />
            Visualizar
          </Button>
          <Button size="sm" variant="outline" className="gap-2" onClick={() => void handleExportHtml()}>
            <FileCode2 className="h-4 w-4" />
            HTML
          </Button>
          <Button size="sm" variant="outline" className="gap-2" onClick={() => void handleExportPdf()} disabled={!isAprovado}>
            <Download className="h-4 w-4" />
            PDF
          </Button>

          {painel.diario.status === "rascunho" && isEngenheiro && (
            <Button size="sm" onClick={() => handleTransicao("submeter")} disabled={transicao.isPending}>
              Submeter
            </Button>
          )}
          {painel.diario.status === "em_revisao" && isAdmin && (
            <>
              <Button size="sm" variant="outline" onClick={() => handleTransicao("rejeitar")} disabled={transicao.isPending}>Rejeitar</Button>
              <Button size="sm" onClick={() => handleTransicao("aprovar")} disabled={transicao.isPending}>Aprovar</Button>
            </>
          )}
          {painel.diario.status === "aprovado" && isAdmin && (
            <Button size="sm" variant="outline" onClick={() => handleTransicao("reabrir")} disabled={transicao.isPending}>Reabrir</Button>
          )}
          {painel.diario.status === "reaberto" && isEngenheiro && (
            <Button size="sm" onClick={() => handleTransicao("submeter")} disabled={transicao.isPending}>Re-submeter</Button>
          )}
        </div>
      </div>

      {/* Aprovado banner */}
      {isAprovado && (
        <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          Diário aprovado — edição bloqueada.
          {painel.diario.pdf_path && (
            <Button size="sm" variant="ghost" className="ml-auto gap-2 text-emerald-400 hover:text-emerald-300" onClick={() => void handleDownloadSavedPdf()}>
              <Download className="h-4 w-4" />Baixar PDF salvo
            </Button>
          )}
        </div>
      )}

      {/* Modo edição ativo — banner */}
      {editMode && (
        <div className="rounded-lg border border-primary/30 bg-primary/8 px-4 py-3 text-sm text-primary flex items-center gap-2">
          <Pencil className="h-4 w-4 shrink-0" />
          Modo edição ativo — adicione, edite ou remova registros. Clique nos campos para editar inline.
        </div>
      )}

      {/* Alertas */}
      {alertasAtivos.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Alertas ({alertasAtivos.length})
          </h2>
          {alertasAtivos.map((alerta) => (
            <AlertCard key={alerta.id} alerta={alerta}
              onResolve={() => void runMutationWithToast(() => resolverAlerta.mutateAsync(alerta.id), "Alerta resolvido")} />
          ))}
        </div>
      )}

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Efetivo" icon={<Users className="h-4 w-4 text-blue-400" />} count={painel.total_efetivo.geral}>
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

        <SectionCard title="Fotos" icon={<Camera className="h-4 w-4 text-pink-400" />} count={painel.fotos.length}>
          <FotosBlock items={painel.fotos} />
        </SectionCard>
      </div>

      {/* Audit trail */}
      <div className="border-t pt-4">
        <Button variant="ghost" size="sm" className="gap-2" onClick={() => setShowAudit(!showAudit)}>
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
                {auditoria.data.map((log) => <AuditRow key={log.id} log={log} />)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
