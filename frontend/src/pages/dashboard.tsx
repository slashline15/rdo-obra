import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useObras } from "@/hooks/use-diario";
import { format, subDays, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  BarChart3,
  Users,
  Activity,
  Clock,
  Package,
  CloudRain,
  TrendingUp,
  AlertCircle,
  Info,
  Calendar,
  Layers,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import type { ReactNode } from "react";

interface DashboardResponse {
  obra: { id: number; nome: string };
  periodo: { inicio: string; fim: string; dias: number };
  kpis: {
    produtividade_media: number;
    dias_improdutivos: number;
    atividades_atrasadas: number;
    tempo_medio_aprovacao_horas: number;
    total_efetivo_periodo: number;
    materiais_pendentes: number;
  };
  tendencias: {
    efetivo_diario: Array<{ data: string; total: number }>;
    atividades_diario: Array<{ data: string; total: number }>;
  };
}

interface Insight {
  texto: string;
  severidade: string;
  data_ref: string | null;
  evidencia: string;
}

function KPICard({
  title,
  value,
  icon,
  subtitle,
  trend,
}: {
  title: string;
  value: string | number;
  icon: ReactNode;
  subtitle?: string;
  trend?: { value: string; positive: boolean };
}) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border bg-card/50 p-5 shadow-sm transition-all hover:bg-card hover:shadow-md backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted/50 text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary transition-colors">
          {icon}
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider ${trend.positive ? "text-emerald-500" : "text-amber-500"}`}>
            {trend.positive ? "↑" : "↓"} {trend.value}
          </div>
        )}
      </div>
      <div className="mt-4">
        <p className="text-2xl font-bold tracking-tight">{value}</p>
        <div className="mt-1 flex items-center justify-between">
          <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {title}
          </span>
          {subtitle && (
            <span className="text-[10px] text-muted-foreground/60">{subtitle}</span>
          )}
        </div>
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border bg-background/95 p-3 shadow-xl backdrop-blur-md">
        <p className="mb-2 text-xs font-semibold text-muted-foreground">
          {label ? format(parseISO(label), "dd 'de' MMMM", { locale: ptBR }) : ""}
        </p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <p className="text-sm font-bold">
              {entry.value} <span className="text-[10px] font-normal text-muted-foreground uppercase">{entry.name}</span>
            </p>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function DashboardPage() {
  const { data: obras } = useObras();
  const [obraId, setObraId] = useState<number | null>(null);
  const hoje = format(new Date(), "yyyy-MM-dd");
  const inicio = format(subDays(new Date(), 30), "yyyy-MM-dd");

  const selectedObraId = obraId ?? obras?.[0]?.id ?? null;

  const { data: dashData, isLoading: kpisLoading } = useQuery({
    queryKey: ["dashboard-kpis", selectedObraId, inicio, hoje],
    queryFn: () =>
      apiGet<DashboardResponse>(
        `/dashboard/${selectedObraId}?data_inicio=${inicio}&data_fim=${hoje}`
      ),
    enabled: !!selectedObraId,
  });

  const { data: insights } = useQuery({
    queryKey: ["dashboard-insights", selectedObraId, inicio, hoje],
    queryFn: () =>
      apiGet<Insight[]>(
        `/dashboard/${selectedObraId}/insights?data_inicio=${inicio}&data_fim=${hoje}`
      ),
    enabled: !!selectedObraId,
  });

  const chartData = useMemo(() => {
    if (!dashData?.tendencias) return [];
    const map = new Map();
    (dashData.tendencias.efetivo_diario ?? []).forEach((d) => {
      map.set(d.data, { data: d.data, efetivo: d.total, atividades: 0 });
    });
    (dashData.tendencias.atividades_diario ?? []).forEach((d) => {
      const existing = map.get(d.data) || { data: d.data, efetivo: 0 };
      map.set(d.data, { ...existing, atividades: d.total });
    });
    return Array.from(map.values()).sort((a, b) => a.data.localeCompare(b.data));
  }, [dashData]);

  const kpis = dashData?.kpis;

  return (
    <div className="min-h-screen bg-background/50 p-6 lg:p-10">
      <div className="mx-auto max-w-7xl space-y-8">
        {/* Header */}
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="h-2 w-8 rounded-full bg-primary" />
              <h1 className="text-3xl font-bold tracking-tight">Canteiro Inteligente</h1>
            </div>
            <p className="text-sm text-muted-foreground">
              Análise executiva dos últimos 30 dias de operação
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-xl border bg-card/50 px-3 py-1.5 shadow-sm backdrop-blur">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs font-medium">{format(parseISO(inicio), "dd/MM")} — {format(parseISO(hoje), "dd/MM")}</span>
            </div>
            {obras && obras.length > 0 && (
              <select
                value={selectedObraId ?? ""}
                onChange={(e) => setObraId(Number(e.target.value))}
                className="h-10 rounded-xl border border-input bg-card px-4 text-sm font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all cursor-pointer"
              >
                {obras.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.nome}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {kpisLoading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-32 animate-pulse rounded-2xl bg-muted/50 border" />
            ))
          ) : kpis ? (
            <>
              <KPICard
                title="Produtividade"
                value={kpis.produtividade_media.toFixed(1)}
                icon={<TrendingUp className="h-5 w-5" />}
                subtitle="atividades/dia"
                trend={{ value: "+12%", positive: true }}
              />
              <KPICard
                title="Improdutividade"
                value={kpis.dias_improdutivos}
                icon={<CloudRain className="h-5 w-5" />}
                subtitle="dias parados"
              />
              <KPICard
                title="Atrasos"
                value={kpis.atividades_atrasadas}
                icon={<Clock className="h-5 w-5" />}
                subtitle="em andamento"
                trend={{ value: "High", positive: false }}
              />
              <KPICard
                title="Ciclo Approval"
                value={`${kpis.tempo_medio_aprovacao_horas.toFixed(0)}h`}
                icon={<Activity className="h-5 w-5" />}
                subtitle="tempo médio"
              />
              <KPICard
                title="Efetivo Médio"
                value={Math.round(kpis.total_efetivo_periodo / (dashData?.periodo.dias || 1))}
                icon={<Users className="h-5 w-5" />}
                subtitle="homens/dia"
              />
              <KPICard
                title="Pendências"
                value={kpis.materiais_pendentes}
                icon={<Package className="h-5 w-5" />}
                subtitle="materiais"
              />
            </>
          ) : null}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Efetivo Trend */}
          <div className="rounded-3xl border bg-card/30 p-6 shadow-sm backdrop-blur-md">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Efetivo Diário</h3>
                <p className="text-xs text-muted-foreground/60">Flutuação de mão de obra no período</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Users className="h-4 w-4" />
              </div>
            </div>
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorEfetivo" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="data"
                    hide
                  />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="efetivo"
                    name="Efetivo"
                    stroke="var(--color-primary)"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorEfetivo)"
                    animationDuration={1500}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Atividades Trend */}
          <div className="rounded-3xl border bg-card/30 p-6 shadow-sm backdrop-blur-md">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Conclusões</h3>
                <p className="text-xs text-muted-foreground/60">Entregas diárias finalizadas</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500">
                <Layers className="h-4 w-4" />
              </div>
            </div>
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="data" hide />
                  <YAxis hide />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar
                    dataKey="atividades"
                    name="Atividades"
                    radius={[4, 4, 0, 0]}
                    animationDuration={1500}
                  >
                    {chartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.atividades > 0 ? "oklch(0.65 0.16 130)" : "oklch(0.62 0.20 38 / 0.1)"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Insights Section */}
        {insights && insights.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="h-4 w-4 text-primary">
                <Sparkles className="h-full w-full" />
              </div>
              <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">Motor de Insights</h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {insights.map((insight, i) => (
                <div
                  key={i}
                  className={`group relative overflow-hidden rounded-2xl border p-5 shadow-sm transition-all hover:shadow-md backdrop-blur-sm ${
                    insight.severidade === "critico"
                      ? "border-red-500/20 bg-red-500/5 hover:bg-red-500/10"
                      : insight.severidade === "atencao"
                      ? "border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10"
                      : "border-primary/20 bg-primary/5 hover:bg-primary/10"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        {insight.severidade === "critico" ? (
                          <AlertCircle className="h-4 w-4 text-red-500" />
                        ) : insight.severidade === "atencao" ? (
                          <AlertCircle className="h-4 w-4 text-amber-500" />
                        ) : (
                          <Info className="h-4 w-4 text-primary" />
                        )}
                        <span className={`text-[10px] font-bold uppercase tracking-tighter ${
                          insight.severidade === "critico" ? "text-red-500" : insight.severidade === "atencao" ? "text-amber-500" : "text-primary"
                        }`}>
                          {insight.severidade}
                        </span>
                      </div>
                      <p className="text-sm font-semibold leading-snug">{insight.texto}</p>
                      <p className="text-xs text-muted-foreground/70">{insight.evidencia}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const Sparkles = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    <path d="M5 3v4" />
    <path d="M19 17v4" />
    <path d="M3 5h4" />
    <path d="M17 19h4" />
  </svg>
);
