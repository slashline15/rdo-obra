import { Link, useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import {
  HardHat,
  Moon,
  Sun,
  Users,
  CalendarRange,
  ListTodo,
  BookOpenText,
  Package,
  Settings,
  BarChart3,
  LogOut,
} from "lucide-react";
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
    <div className="min-h-screen flex bg-background">
      <aside className="w-64 border-r bg-sidebar text-sidebar-foreground flex flex-col shrink-0 shadow-lg">
        {/* Top Branding Accent */}
        <div className="h-1 w-full bg-gradient-to-r from-primary to-primary/40 shrink-0" />

        {/* Logo Section */}
        <div className="px-5 py-6 border-b flex items-center gap-3 group cursor-pointer" onClick={() => navigate({ to: "/obras" })}>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20 shadow-[0_0_15px_rgba(var(--primary-rgb),0.1)] group-hover:scale-105 transition-transform">
             <img src="/logo.png" alt="RDO" className="h-6 w-6 object-contain" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="block font-black text-base leading-tight tracking-tighter uppercase italic">RDO <span className="text-primary tracking-normal not-italic font-bold">Digital</span></span>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest block opacity-60">Engineering OS</span>
          </div>
        </div>

        {/* Nav principal */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto custom-scrollbar">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/50 px-2 py-3">Execução</p>
          <NavItem to="/obras" icon={HardHat} label="Canteiro de Obras" />
          <NavItem to="/dashboard" icon={BarChart3} label="Insights & BI" />
          <NavItem to="/usuarios" icon={Users} label="Time & Acessos" />

          <div className="pt-4">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/50 px-2 py-3">Painel Gerencial</p>
            <FutureNavItem icon={CalendarRange} label="Cronograma Master" />
            <FutureNavItem icon={ListTodo} label="Plano de Ataque" />
            <FutureNavItem icon={Package} label="Suprimentos" />
          </div>

          <div className="pt-4">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/50 px-2 py-3">Sistema</p>
            <NavItem to="/docs" icon={BookOpenText} label="Documentação" />
            <FutureNavItem icon={Settings} label="Configurações" />
          </div>
        </nav>

        {/* Rodapé do Sidebar */}
        <div className="p-4 border-t bg-muted/5">
          <div className="flex items-center gap-3 px-3 py-3 rounded-2xl bg-background/40 border border-border/50 backdrop-blur-sm group hover:border-primary/30 transition-colors">
            <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-bold text-primary border border-primary/20">
              {user?.nome?.substring(0, 2).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold truncate leading-tight">{user?.nome}</p>
              <p className="text-[10px] text-muted-foreground truncate uppercase font-medium">{user?.role}</p>
            </div>
            <button onClick={handleLogout} className="p-1.5 text-muted-foreground hover:text-destructive transition-colors">
              <LogOut className="h-4 w-4" />
            </button>
          </div>

          <div className="flex items-center justify-between mt-4 px-2">
             <button
              onClick={toggleTheme}
              className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground hover:text-primary transition-colors"
            >
              {theme === "dark" ? <Sun className="h-3 w-3" /> : <Moon className="h-3 w-3" />}
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </button>
            <div className="flex items-center gap-1.5">
               <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
               <span className="text-[9px] font-bold text-muted-foreground/40 uppercase">V 0.8.2</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-background">
        {children}
      </main>
    </div>
  );
}
