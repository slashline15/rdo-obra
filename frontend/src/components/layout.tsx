import { Link, useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import {
  ClipboardList,
  BarChart3,
  LogOut,
  HardHat,
  Moon,
  Sun,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ReactNode } from "react";

const NAV_ITEMS = [
  { to: "/obras", label: "Obras", icon: HardHat },
  { to: "/dashboard", label: "Dashboard", icon: BarChart3 },
] as const;

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate({ to: "/login" });
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-sidebar text-sidebar-foreground flex flex-col">
        <div className="p-4 border-b space-y-4">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <ClipboardList className="h-5 w-5" />
            </div>
            <div>
              <span className="block font-bold text-lg leading-none">RDO Digital</span>
              <span className="text-xs text-muted-foreground">Painel de obra</span>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="w-full justify-between"
            onClick={toggleTheme}
          >
            <span>{theme === "dark" ? "Tema escuro" : "Tema claro"}</span>
            {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </Button>
        </div>

        <div className="px-4 pt-4">
          <div className="rounded-2xl border border-sidebar-border/80 bg-background/50 p-3">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Navegação</p>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium hover:bg-sidebar-accent transition-colors [&.active]:bg-sidebar-accent [&.active]:text-sidebar-accent-foreground"
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="p-3 border-t space-y-2">
          <div className="rounded-2xl border border-sidebar-border/80 bg-background/50 px-3 py-3">
            <p className="text-sm font-medium truncate">{user?.nome}</p>
            <p className="text-xs text-muted-foreground">{user?.role}</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            Sair
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-background">
        {children}
      </main>
    </div>
  );
}
