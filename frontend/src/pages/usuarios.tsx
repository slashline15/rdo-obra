import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Ban, CheckCircle2, Copy, HardHat, Link2, Plus, RotateCcw, ShieldCheck, Users, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiGet } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useConvites, useCriarConvite, useObras, useReenviarConvite, useRevogarConvite, type InviteItem } from "@/hooks/use-diario";
import { toast } from "sonner";

interface Usuario {
  id: number;
  nome: string;
  telefone: string;
  email: string | null;
  role: string;
  obra_id: number | null;
  ativo: boolean;
  nivel_acesso: number;
  pode_aprovar_diario: boolean;
  registro_profissional: string | null;
  empresa_vinculada: string | null;
}

const ROLE_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  admin: { label: "Admin Geral", icon: <ShieldCheck className="h-3.5 w-3.5" />, color: "text-primary bg-primary/15 border-primary/25" },
  responsavel: { label: "Co-responsável", icon: <ShieldCheck className="h-3.5 w-3.5" />, color: "text-amber-500 bg-amber-500/10 border-amber-500/20" },
  engenheiro: { label: "Engenheiro", icon: <HardHat className="h-3.5 w-3.5" />, color: "text-blue-400 bg-blue-400/10 border-blue-400/20" },
  encarregado: { label: "Operacional", icon: <Wrench className="h-3.5 w-3.5" />, color: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
  mestre: { label: "Operacional", icon: <Wrench className="h-3.5 w-3.5" />, color: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
};

const LEVEL_LABEL: Record<number, string> = {
  1: "Nível 1",
  2: "Nível 2",
  3: "Nível 3",
};

function RoleBadge({ role }: { role: string }) {
  const cfg = ROLE_CONFIG[role] ?? { label: role, icon: null, color: "text-muted-foreground bg-muted border-border" };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

function InviteStatusBadge({ status }: { status: string }) {
  const cls =
    status === "aceito"
      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      : status === "expirado"
        ? "text-muted-foreground bg-muted border-border"
        : "text-amber-400 bg-amber-500/10 border-amber-500/20";
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${cls}`}>{status}</span>;
}

function getInitials(nome: string) {
  return nome.split(" ").slice(0, 2).map((p) => p[0]).join("").toUpperCase();
}

function copyText(value: string, label: string) {
  navigator.clipboard.writeText(value)
    .then(() => toast.success(`${label} copiado`))
    .catch(() => toast.error(`Não foi possível copiar ${label.toLowerCase()}`));
}

function InviteRow({
  invite,
  onReissue,
  onRevoke,
}: {
  invite: InviteItem;
  onReissue: (invite: InviteItem) => void;
  onRevoke: (invite: InviteItem) => void;
}) {
  return (
    <div className="rounded-xl border bg-card p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{invite.email}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <InviteStatusBadge status={invite.status} />
            <RoleBadge role={invite.role} />
            <span className="text-xs text-muted-foreground">{LEVEL_LABEL[invite.nivel_acesso] ?? `Nível ${invite.nivel_acesso}`}</span>
            {invite.pode_aprovar_diario && (
              <span className="text-xs text-sky-400">aprova diário</span>
            )}
          </div>
        </div>
        <span className="text-xs text-muted-foreground">
          expira {new Date(invite.expira_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
        </span>
      </div>
      <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
        <div className="rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground break-all">
          Token original disponível apenas no momento da emissão. Status atual preservado para auditoria.
        </div>
        <div className="md:col-span-2 flex flex-wrap items-center justify-end gap-2">
          {invite.status !== "aceito" && invite.status !== "revogado" && (
            <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => onReissue(invite)}>
              <RotateCcw className="h-3.5 w-3.5" />
              Reenviar
            </Button>
          )}
          {invite.status === "pendente" && (
            <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => onRevoke(invite)}>
              <Ban className="h-3.5 w-3.5" />
              Revogar
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function UsuariosPage() {
  const { user, isAdmin, isEngenheiro, canApproveDiario } = useAuth();
  const { data: obras } = useObras();
  const [email, setEmail] = useState("");
  const [telefone, setTelefone] = useState("");
  const [cargo, setCargo] = useState("");
  const [obraId, setObraId] = useState<number | null>(null);
  const [nivelAcesso, setNivelAcesso] = useState<number>(isAdmin ? 3 : 3);
  const [role, setRole] = useState("encarregado");
  const [podeAprovar, setPodeAprovar] = useState(false);
  const [lastInvite, setLastInvite] = useState<{ token: string; email: string } | null>(null);
  const effectiveObraId = isAdmin ? obraId ?? obras?.[0]?.id ?? null : user?.obra_id ?? null;

  const { data: usuarios, isLoading } = useQuery({
    queryKey: ["usuarios"],
    queryFn: () => apiGet<Usuario[]>("/usuarios/"),
    enabled: isEngenheiro,
  });

  const { data: convites, isLoading: invitesLoading } = useConvites(effectiveObraId, isEngenheiro);
  const criarConvite = useCriarConvite();
  const reenviarConvite = useReenviarConvite();
  const revogarConvite = useRevogarConvite();

  const roleOptions = isAdmin
    ? [
        { value: "admin", label: "Admin Geral", level: 1 },
        { value: "responsavel", label: "Co-responsável", level: 2 },
        { value: "engenheiro", label: "Engenheiro", level: 2 },
        { value: "encarregado", label: "Operacional", level: 3 },
      ]
    : [
        { value: "encarregado", label: "Operacional", level: 3 },
        { value: "mestre", label: "Operacional", level: 3 },
      ];

  async function handleInviteSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;

    try {
      const selectedRole = roleOptions.find((item) => item.value === role);
      const nextLevel = selectedRole?.level ?? nivelAcesso;
      const payload = await criarConvite.mutateAsync({
        email: email.trim(),
        telefone: telefone.trim() || undefined,
        cargo: cargo.trim() || undefined,
        obra_id: effectiveObraId,
        role,
        nivel_acesso: nextLevel,
        pode_aprovar_diario: nextLevel === 2 ? podeAprovar : false,
      });
      setLastInvite({ token: payload.token, email: payload.invite.email });
      setEmail("");
      setTelefone("");
      setCargo("");
      setRole(isAdmin ? "encarregado" : "encarregado");
      setNivelAcesso(3);
      setPodeAprovar(false);
      toast.success("Convite gerado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao gerar convite");
    }
  }

  async function handleReissue(invite: InviteItem) {
    try {
      const payload = await reenviarConvite.mutateAsync(invite.id);
      setLastInvite({ token: payload.token, email: payload.invite.email });
      toast.success("Convite reemitido");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao reenviar convite");
    }
  }

  async function handleRevoke(invite: InviteItem) {
    try {
      await revogarConvite.mutateAsync(invite.id);
      toast.success("Convite revogado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao revogar convite");
    }
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Usuários</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {usuarios?.length ?? "—"} cadastrados
          </p>
        </div>
        <div className="rounded-xl border bg-card px-4 py-3 text-sm">
          <p className="font-medium">{isAdmin ? "Admin Geral" : "Co-responsável"}</p>
          <p className="text-muted-foreground text-xs mt-1">
            Convites e gestão filtrados pelo seu escopo.
          </p>
        </div>
      </div>

      {!isEngenheiro && (
        <div className="rounded-2xl border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
          Esta área é exclusiva para nível 1 e nível 2.
        </div>
      )}

      {isEngenheiro && (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div className="rounded-2xl border bg-card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/15 text-primary border border-primary/25">
                <Plus className="h-4 w-4" />
              </div>
              <div>
                <h2 className="font-semibold">Novo convite</h2>
                <p className="text-sm text-muted-foreground">Gere um link nominal para ativação de acesso.</p>
              </div>
            </div>

            <form onSubmit={handleInviteSubmit} className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1.5 text-sm">
                <span className="font-medium">Email</span>
                <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="novo@empresa.com" required />
              </label>
              <label className="space-y-1.5 text-sm">
                <span className="font-medium">Telefone</span>
                <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={telefone} onChange={(e) => setTelefone(e.target.value)} placeholder="5511999999999" />
              </label>
              <label className="space-y-1.5 text-sm">
                <span className="font-medium">Cargo</span>
                <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={cargo} onChange={(e) => setCargo(e.target.value)} placeholder="Técnico de campo" />
              </label>
              {isAdmin && (
                <label className="space-y-1.5 text-sm">
                  <span className="font-medium">Obra</span>
                  <select className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={effectiveObraId ?? ""} onChange={(e) => setObraId(e.target.value ? Number(e.target.value) : null)}>
                    <option value="">Sem obra vinculada</option>
                    {obras?.map((obra) => (
                      <option key={obra.id} value={obra.id}>{obra.nome}</option>
                    ))}
                  </select>
                </label>
              )}
              <label className="space-y-1.5 text-sm">
                <span className="font-medium">Perfil</span>
                <select
                  className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm"
                  value={role}
                  onChange={(e) => {
                    const nextRole = e.target.value;
                    setRole(nextRole);
                    const selectedRole = roleOptions.find((item) => item.value === nextRole);
                    setNivelAcesso(selectedRole?.level ?? 3);
                    if ((selectedRole?.level ?? 3) !== 2) setPodeAprovar(false);
                  }}
                >
                  {roleOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-1.5 text-sm">
                <span className="font-medium">Nível de acesso</span>
                <input className="h-10 w-full rounded-lg border border-input bg-muted px-3 text-sm text-muted-foreground" value={LEVEL_LABEL[nivelAcesso] ?? `Nível ${nivelAcesso}`} readOnly />
              </label>

              {nivelAcesso === 2 && (
                <label className="md:col-span-2 flex items-center gap-3 rounded-xl border border-sky-500/20 bg-sky-500/8 px-4 py-3 text-sm">
                  <input type="checkbox" checked={podeAprovar} onChange={(e) => setPodeAprovar(e.target.checked)} disabled={!isAdmin && !canApproveDiario} />
                  <span>Delegar segunda assinatura e aprovação de diário</span>
                </label>
              )}

              <div className="md:col-span-2 flex items-center justify-between gap-3 pt-2">
                <p className="text-xs text-muted-foreground">
                  O convite expira automaticamente e exige cadastro completo do destinatário.
                </p>
                <Button type="submit" size="sm" className="gap-2" disabled={criarConvite.isPending}>
                  <Plus className="h-3.5 w-3.5" />
                  {criarConvite.isPending ? "Gerando..." : "Gerar convite"}
                </Button>
              </div>
            </form>
          </div>

          <div className="rounded-2xl border bg-card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <h2 className="font-semibold">Último convite</h2>
            </div>
            {!lastInvite ? (
              <p className="text-sm text-muted-foreground">Gere um convite para copiar o link de ativação.</p>
            ) : (
              <div className="space-y-3">
                <p className="text-sm">{lastInvite.email}</p>
                <div className="rounded-xl bg-muted/50 px-3 py-2 text-xs break-all">
                  {window.location.origin}/convite/{lastInvite.token}
                </div>
                <div className="flex gap-2">
                  <Button type="button" size="sm" variant="outline" className="gap-2" onClick={() => copyText(`${window.location.origin}/convite/${lastInvite.token}`, "Link")}>
                    <Link2 className="h-3.5 w-3.5" />
                    Copiar link
                  </Button>
                  <Button type="button" size="sm" variant="outline" className="gap-2" onClick={() => copyText(lastInvite.token, "Token")}>
                    <Copy className="h-3.5 w-3.5" />
                    Copiar token
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-lg font-semibold">Convites emitidos</h2>
            <p className="text-sm text-muted-foreground">Acompanhe convites pendentes, aceitos e expirados.</p>
          </div>
        </div>

        {invitesLoading ? (
          <div className="grid gap-3">
            {[1, 2].map((i) => <div key={i} className="h-28 rounded-2xl bg-muted animate-pulse" />)}
          </div>
        ) : !convites?.length ? (
          <div className="rounded-2xl border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
            Nenhum convite emitido neste escopo.
          </div>
        ) : (
          <div className="grid gap-3">
            {convites.map((invite) => (
              <InviteRow
                key={invite.id}
                invite={invite}
                onReissue={handleReissue}
                onRevoke={handleRevoke}
              />
            ))}
          </div>
        )}
      </section>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !usuarios?.length ? (
        <div className="text-center py-20 text-muted-foreground">
          <Users className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p>Nenhum usuário encontrado.</p>
        </div>
      ) : (
        <div className="border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/40">
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide px-4 py-3">Usuário</th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide px-4 py-3">Contato</th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide px-4 py-3">Perfil</th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide px-4 py-3">Nível</th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u, i) => (
                <tr key={u.id} className={`border-b last:border-0 hover:bg-muted/30 transition-colors ${i % 2 === 0 ? "" : "bg-muted/10"}`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-primary/15 border border-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                        {getInitials(u.nome)}
                      </div>
                      <div>
                        <span className="text-sm font-medium block">{u.nome}</span>
                        {u.registro_profissional && (
                          <span className="text-xs text-muted-foreground">{u.registro_profissional}</span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm">{u.email ?? u.telefone}</p>
                    <p className="text-xs text-muted-foreground">{u.email ? u.telefone : u.empresa_vinculada ?? "Sem empresa vinculada"}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <RoleBadge role={u.role} />
                      {u.pode_aprovar_diario && <span className="text-xs text-sky-400">aprova diário</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm">{LEVEL_LABEL[u.nivel_acesso] ?? `Nível ${u.nivel_acesso}`}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${u.ativo ? "text-emerald-400" : "text-muted-foreground"}`}>
                      {u.ativo ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
