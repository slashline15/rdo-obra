import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { Users, ShieldCheck, HardHat, Wrench, Plus } from "lucide-react";

interface Usuario {
  id: number;
  nome: string;
  telefone: string;
  email: string | null;
  role: string;
  obra_id: number | null;
  ativo: boolean;
}

const ROLE_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  admin: { label: "Admin", icon: <ShieldCheck className="h-3.5 w-3.5" />, color: "text-primary bg-primary/15 border-primary/25" },
  responsavel: { label: "Responsável", icon: <ShieldCheck className="h-3.5 w-3.5" />, color: "text-amber-500 bg-amber-500/10 border-amber-500/20" },
  engenheiro: { label: "Engenheiro", icon: <HardHat className="h-3.5 w-3.5" />, color: "text-blue-400 bg-blue-400/10 border-blue-400/20" },
  mestre: { label: "Mestre", icon: <Wrench className="h-3.5 w-3.5" />, color: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
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

function getInitials(nome: string) {
  return nome.split(" ").slice(0, 2).map((p) => p[0]).join("").toUpperCase();
}

export default function UsuariosPage() {
  const { data: usuarios, isLoading } = useQuery({
    queryKey: ["usuarios"],
    queryFn: () => apiGet<Usuario[]>("/usuarios/"),
  });

  return (
    <div className="p-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Usuários</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {usuarios?.length ?? "—"} cadastrados
          </p>
        </div>
        <button className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-border text-sm text-muted-foreground hover:border-primary/50 hover:text-primary transition-colors">
          <Plus className="h-4 w-4" />
          Novo usuário
        </button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && !usuarios?.length && (
        <div className="text-center py-20 text-muted-foreground">
          <Users className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p>Nenhum usuário encontrado.</p>
        </div>
      )}

      {!isLoading && !!usuarios?.length && (
        <div className="border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/40">
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide px-4 py-3">Usuário</th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide px-4 py-3">Contato</th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide px-4 py-3">Perfil</th>
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
                      <span className="text-sm font-medium">{u.nome}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm">{u.email ?? u.telefone}</p>
                    {u.email && <p className="text-xs text-muted-foreground">{u.telefone}</p>}
                  </td>
                  <td className="px-4 py-3">
                    <RoleBadge role={u.role} />
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
