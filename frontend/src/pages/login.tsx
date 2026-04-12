import { useState, useEffect, type FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { ClipboardList, MessageSquareText, ShieldCheck, Sparkles } from "lucide-react";

export default function LoginPage() {
  const { user, loading: authLoading, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (!authLoading && user) {
      navigate({ to: "/obras" });
    }
  }, [user, authLoading, navigate]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate({ to: "/obras" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao fazer login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(255,145,77,0.14),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(32,120,255,0.11),_transparent_26%),linear-gradient(180deg,var(--background),var(--background))]">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl items-center px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="flex flex-col justify-center space-y-6">
            <div className="inline-flex items-center gap-2 self-start rounded-full border bg-card/80 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Entrada rápida para equipe de obra
            </div>

            <div className="space-y-4">
              <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
                RDO digital que já entra pronto para operar e vender.
              </h1>
              <p className="max-w-xl text-base text-muted-foreground sm:text-lg">
                Registre pelo painel, WhatsApp ou Telegram, gere HTML/PDF do diário e acompanhe a obra com rastreabilidade
                real. Menos planilha solta, mais entrega que dá para mostrar ao cliente.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                {
                  icon: MessageSquareText,
                  title: "Mensageria",
                  text: "WhatsApp e Telegram no fluxo do canteiro.",
                },
                {
                  icon: ClipboardList,
                  title: "RDO pronto",
                  text: "Preview HTML e PDF gerado com um clique.",
                },
                {
                  icon: ShieldCheck,
                  title: "Auditável",
                  text: "Histórico e trilha de mudanças no banco.",
                },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.title} className="rounded-2xl border bg-card/80 p-4 shadow-sm backdrop-blur">
                    <Icon className="h-4 w-4 text-primary" />
                    <p className="mt-3 text-sm font-semibold">{item.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.text}</p>
                  </div>
                );
              })}
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                to="/apresentacao"
                className="inline-flex h-10 items-center justify-center rounded-lg border border-border bg-background px-4 text-sm font-medium shadow-sm transition-colors hover:bg-muted"
              >
                Ver apresentação
              </Link>
              <a
                href="#acesso"
                className="inline-flex h-10 items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
              >
                Ir para o acesso
              </a>
            </div>
          </section>

          <section id="acesso" className="flex items-center justify-center">
            <div className="w-full max-w-md rounded-3xl border bg-card p-6 shadow-[0_24px_80px_rgba(0,0,0,0.12)]">
              <div className="mb-6 space-y-1 text-center">
                <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">Acesso operacional</p>
                <h2 className="text-2xl font-semibold tracking-tight">Entrar no painel</h2>
                <p className="text-sm text-muted-foreground">Use o acesso já liberado para sua equipe.</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="username">
                    Email
                  </label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="flex h-11 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    placeholder="voce@empresa.com"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="password">
                    Senha
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="flex h-11 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    required
                  />
                </div>

                {error && (
                  <p className="text-sm font-medium text-destructive">{error}</p>
                )}

                <Button type="submit" className="w-full h-11" disabled={loading}>
                  {loading ? "Entrando..." : "Entrar"}
                </Button>
              </form>

              <p className="mt-4 text-center text-xs text-muted-foreground">
                Precisa ver antes?{" "}
                <Link to="/apresentacao" className="font-medium text-primary hover:underline">
                  abra a apresentação pública
                </Link>
                .
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
