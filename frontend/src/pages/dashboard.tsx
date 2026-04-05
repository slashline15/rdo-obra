import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useObras } from "@/hooks/use-diario";
import { format, subDays } from "date-fns";
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
} from "lucide-react";
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
}: {
  title: string;
  value: string | number;
  icon: ReactNode;
  subtitle?: string;
}) {
  return (
    <div className="border rounded-lg bg-card p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground font-medium">{title}</span>
        {icon}
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
    </div>
  );
}

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
  const kpis = dashData?.kpis;

  const { data: insights } = useQuery({
    queryKey: ["dashboard-insights", selectedObraId, inicio, hoje],
    queryFn: () =>
      apiGet<Insight[]>(
        `/dashboard/${selectedObraId}/insights?data_inicio=${inicio}&data_fim=${hoje}`
      ),
    enabled: !!selectedObraId,
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Últimos 30 dias</p>
        </div>

        {obras && obras.length > 1 && (
          <select
            value={selectedObraId ?? ""}
            onChange={(e) => setObraId(Number(e.target.value))}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            {obras.map((o) => (
              <option key={o.id} value={o.id}>
                {o.nome}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* KPI Cards */}
      {kpisLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-28 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      ) : kpis ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <KPICard
            title="Produtividade"
            value={kpis.produtividade_media.toFixed(1)}
            icon={<TrendingUp className="h-4 w-4 text-green-600" />}
            subtitle="atividades/dia"
          />
          <KPICard
            title="Dias Improdutivos"
            value={kpis.dias_improdutivos}
            icon={<CloudRain className="h-4 w-4 text-blue-500" />}
            subtitle="no período"
          />
          <KPICard
            title="Atrasadas"
            value={kpis.atividades_atrasadas}
            icon={<Activity className="h-4 w-4 text-red-500" />}
            subtitle="atividades"
          />
          <KPICard
            title="Tempo Aprovação"
            value={`${kpis.tempo_medio_aprovacao_horas.toFixed(0)}h`}
            icon={<Clock className="h-4 w-4 text-amber-500" />}
            subtitle="média"
          />
          <KPICard
            title="Efetivo Total"
            value={kpis.total_efetivo_periodo}
            icon={<Users className="h-4 w-4 text-blue-600" />}
            subtitle="homens-dia"
          />
          <KPICard
            title="Materiais Pendentes"
            value={kpis.materiais_pendentes}
            icon={<Package className="h-4 w-4 text-amber-600" />}
            subtitle="itens"
          />
        </div>
      ) : null}

      {/* Insights */}
      {insights && insights.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Insights
          </h2>
          {insights.map((insight, i) => (
            <div
              key={i}
              className={`flex items-start gap-3 p-3 rounded-lg border ${
                insight.severidade === "critico"
                  ? "border-red-200 bg-red-50"
                  : insight.severidade === "atencao"
                  ? "border-yellow-200 bg-yellow-50"
                  : "border-blue-200 bg-blue-50"
              }`}
            >
              {insight.severidade === "critico" ? (
                <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
              ) : insight.severidade === "atencao" ? (
                <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5 shrink-0" />
              ) : (
                <Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
              )}
              <div>
                <p className="text-sm">{insight.texto}</p>
                <p className="text-xs text-muted-foreground mt-1">{insight.evidencia}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
