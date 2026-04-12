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
  Users,
  Bell,
  CalendarRange,
  ListTodo,
  BookOpenText,
  Package,
  NotebookPen,
  Settings,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ReactNode } from "react";

function NavItem({ to, icon: Icon, label }: { to: string; icon: React.ElementType; label: string }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors [&.active]:bg-sidebar-accent [&.active]:text-primary [&.active]:font-semibold"
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </Link>
  );
}

function FutureNavItem({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  return (
    <span className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground/40 cursor-not-allowed select-none" title="Em breve">
      <Icon className="h-4 w-4 shrink-0" />
      {label}
      <span className="ml-auto text-[9px] uppercase tracking-widest opacity-60">soon</span>
    </span>
  );
}

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
      <aside className="w-60 border-r bg-sidebar text-sidebar-foreground flex flex-col shrink-0">
        {/* Linha primária no topo */}
        <div className="h-0.5 w-full bg-primary shrink-0" />

        {/* Logo + Bell */}
        <div className="px-4 py-4 border-b flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/15 text-primary border border-primary/25">
            <ClipboardList className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="block font-bold text-sm leading-none tracking-tight">RDO Digital</span>
            <span className="text-[11px] text-muted-foreground mt-0.5 block">Painel de obra</span>
          </div>
          <button className="relative p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors" title="Notificações">
            <Bell className="h-4 w-4" />
          </button>
        </div>

        {/* Nav principal */}
        <nav className="flex-1 p-3 pt-4 space-y-0.5 overflow-y-auto">
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground px-2 pb-2">Painel</p>
          <NavItem to="/obras" icon={HardHat} label="Obras" />
          <NavItem to="/dashboard" icon={BarChart3} label="Dashboard" />
          <NavItem to="/usuarios" icon={Users} label="Usuários" />
          <NavItem to="/docs" icon={BookOpenText} label="Helper" />

          <div className="pt-3">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground px-2 pb-2">Planejamento</p>
            <FutureNavItem icon={CalendarRange} label="Planejamento" />
            <FutureNavItem icon={ListTodo} label="Tarefas" />
          </div>

          <div className="pt-3">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground px-2 pb-2">Registros</p>
            <FutureNavItem icon={Package} label="Materiais" />
            <FutureNavItem icon={NotebookPen} label="Anotações" />
          </div>
        </nav>

        {/* Rodapé */}
        <div className="p-3 border-t space-y-1">
          <FutureNavItem icon={Settings} label="Configurações" />
          <div className="px-3 py-2.5 rounded-lg bg-background/50 mt-1">
            <p className="text-sm font-medium truncate">{user?.nome}</p>
            <p className="text-[11px] text-muted-foreground capitalize">{user?.role}</p>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="flex-1 justify-start gap-2 text-muted-foreground hover:text-foreground"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4" />
              Sair
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:text-foreground"
              onClick={toggleTheme}
              title={theme === "dark" ? "Mudar para claro" : "Mudar para escuro"}
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-background">
        {children}
      </main>
    </div>
  );
}
