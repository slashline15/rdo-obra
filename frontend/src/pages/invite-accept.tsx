import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { CheckCircle2, Link2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

interface InviteInfo {
  id: number;
  email: string;
  obra_id: number | null;
  role: string;
  nivel_acesso: number;
  pode_aprovar_diario: boolean;
  cargo: string | null;
  status: string;
  expira_em: string;
}

const LEVEL_LABEL: Record<number, string> = {
  1: "Admin Geral",
  2: "Co-responsável",
  3: "Operacional",
};

export default function InviteAcceptPage() {
  const { token } = useParams({ strict: false }) as { token: string };
  const navigate = useNavigate();
  const [invite, setInvite] = useState<InviteInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [registroProfissional, setRegistroProfissional] = useState("");
  const [empresaVinculada, setEmpresaVinculada] = useState("");

  useEffect(() => {
    let active = true;

    async function loadInvite() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`/api/auth/invites/${encodeURIComponent(token)}`);
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail ?? "Convite inválido");
        if (!active) return;
        setInvite(body);
        setEmail(body.email ?? "");
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Erro ao carregar convite");
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadInvite();
    return () => {
      active = false;
    };
  }, [token]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch("/api/auth/invites/accept", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          nome,
          telefone,
          email,
          senha,
          registro_profissional: registroProfissional || undefined,
          empresa_vinculada: empresaVinculada || undefined,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail ?? "Não foi possível ativar o convite");
      localStorage.setItem("token", body.access_token);
      window.location.href = "/obras";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao ativar convite");
      setSubmitting(false);
    }
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-muted/40"><div className="h-40 w-full max-w-lg rounded-2xl bg-muted animate-pulse" /></div>;
  }

  return (
    <div className="min-h-screen bg-muted/40 px-4 py-10">
      <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[0.9fr_minmax(0,1.1fr)]">
        <section className="rounded-3xl border bg-card p-8 shadow-sm">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/25 bg-primary/15 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="mt-6 space-y-3">
            <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Convite de acesso</p>
            <h1 className="text-3xl font-bold tracking-tight">Ativação do painel RDO</h1>
            <p className="text-sm text-muted-foreground">
              Complete o seu cadastro para ativar o acesso da obra e registrar o vínculo profissional.
            </p>
          </div>

          {invite && (
            <div className="mt-8 space-y-4 rounded-2xl border bg-muted/35 p-5">
              <div className="flex items-center gap-2 text-sm font-medium">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                Convite válido
              </div>
              <div className="space-y-2 text-sm">
                <p><span className="text-muted-foreground">Email:</span> {invite.email}</p>
                <p><span className="text-muted-foreground">Perfil:</span> {LEVEL_LABEL[invite.nivel_acesso] ?? invite.role}</p>
                <p><span className="text-muted-foreground">Cargo:</span> {invite.cargo ?? "Não informado"}</p>
                <p><span className="text-muted-foreground">Expira em:</span> {new Date(invite.expira_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</p>
                {invite.pode_aprovar_diario && (
                  <p className="text-sky-400">Convite com delegação de aprovação de diário.</p>
                )}
              </div>
            </div>
          )}

          <div className="mt-8 rounded-2xl border border-dashed px-4 py-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-2 font-medium text-foreground">
              <Link2 className="h-3.5 w-3.5" />
              Cadastro ativo
            </div>
            <p className="mt-2">O acesso só fica disponível depois do preenchimento de nome real, vínculo profissional e senha.</p>
          </div>
        </section>

        <section className="rounded-3xl border bg-card p-8 shadow-sm">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold">Completar cadastro</h2>
            <p className="text-sm text-muted-foreground">Esses dados serão usados para autenticação e auditoria.</p>
          </div>

          <form onSubmit={handleSubmit} className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="space-y-1.5 text-sm md:col-span-2">
              <span className="font-medium">Nome real</span>
              <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={nome} onChange={(e) => setNome(e.target.value)} required />
            </label>
            <label className="space-y-1.5 text-sm">
              <span className="font-medium">Email</span>
              <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label className="space-y-1.5 text-sm">
              <span className="font-medium">Telefone</span>
              <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={telefone} onChange={(e) => setTelefone(e.target.value)} required />
            </label>
            <label className="space-y-1.5 text-sm">
              <span className="font-medium">Registro profissional</span>
              <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={registroProfissional} onChange={(e) => setRegistroProfissional(e.target.value)} placeholder="CREA / CRT / empresa" />
            </label>
            <label className="space-y-1.5 text-sm">
              <span className="font-medium">Empresa vinculada</span>
              <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={empresaVinculada} onChange={(e) => setEmpresaVinculada(e.target.value)} placeholder="Construtora / terceirizada" />
            </label>
            <label className="space-y-1.5 text-sm md:col-span-2">
              <span className="font-medium">Senha</span>
              <input className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required />
            </label>

            {error && (
              <p className="md:col-span-2 text-sm font-medium text-destructive">{error}</p>
            )}

            <div className="md:col-span-2 flex items-center justify-between gap-3 pt-2">
              <Button type="button" variant="ghost" onClick={() => navigate({ to: "/login" })}>
                Voltar ao login
              </Button>
              <Button type="submit" disabled={submitting || !invite}>
                {submitting ? "Ativando..." : "Ativar acesso"}
              </Button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
