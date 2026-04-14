import { useParams, useNavigate } from "@tanstack/react-router";
import { 
  format, 
  startOfMonth, 
  endOfMonth, 
  eachDayOfInterval, 
  isSameMonth, 
  isSameDay, 
  addMonths, 
  subMonths, 
  parseISO,
  isToday,
  startOfWeek,
  endOfWeek
} from "date-fns";
import { ptBR } from "date-fns/locale";
import { useCalendario, useObras } from "@/hooks/use-diario";
import { useState } from "react";
import { 
  ChevronLeft, 
  ChevronRight, 
  CircleAlert, 
  CheckCircle2, 
  Clock, 
  Calendar as CalendarIcon,
  Search,
  ArrowRight
} from "lucide-react";
import { Button } from "@/components/ui/button";

const STATUS_MAP: Record<string, { color: string; label: string; icon: any }> = {
  aprovado: { color: "bg-emerald-500", label: "Aprovado", icon: CheckCircle2 },
  em_revisao: { color: "bg-amber-500", label: "Em Revisão", icon: Clock },
  rascunho: { color: "bg-sky-500", label: "Rascunho", icon: CircleAlert },
  reaberto: { color: "bg-orange-500", label: "Reaberto", icon: CircleAlert },
  atrasado: { color: "bg-red-500", label: "Atrasado", icon: CircleAlert }, // Virtual status
};

export default function CalendarioPage() {
  const { obraId } = useParams({ strict: false }) as { obraId: string };
  const navigate = useNavigate();
  const [currentDate, setCurrentDate] = useState(new Date());

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const calendarStart = startOfWeek(monthStart, { weekStartsOn: 0 });
  const calendarEnd = endOfWeek(monthEnd, { weekStartsOn: 0 });

  const days = eachDayOfInterval({
    start: calendarStart,
    end: calendarEnd,
  });

  const { data: obras } = useObras();
  const obra = obras?.find(o => o.id === Number(obraId));
  
  const { data: statusList } = useCalendario(
    Number(obraId),
    format(calendarStart, "yyyy-MM-dd"),
    format(calendarEnd, "yyyy-MM-dd")
  );

  function getDayStatus(day: Date) {
    const statusObj = statusList?.find(s => isSameDay(parseISO(s.data), day));
    if (statusObj) return statusObj.status;
    
    // Logic for "overdue": if day < today and no record exists
    if (day < new Date() && !statusObj && isSameMonth(day, monthStart)) {
      return "atrasado";
    }
    return null;
  }

  function handleDayClick(day: Date) {
    navigate({ 
      to: "/obras/$obraId/diario/$data", 
      params: { obraId, data: format(day, "yyyy-MM-dd") } 
    });
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-700">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-primary font-bold uppercase tracking-[0.2em] text-xs">
            <CalendarIcon className="h-4 w-4" />
            Rastreabilidade Temporal
          </div>
          <h1 className="text-4xl font-black tracking-tighter">
            {obra?.nome || "Carregando..."}
          </h1>
          <p className="text-muted-foreground text-sm font-medium">
            Histórico de conformidade e status dos Diários de Obra.
          </p>
        </div>

        <div className="flex items-center bg-card/50 border rounded-2xl p-1.5 backdrop-blur-md shadow-sm">
          <Button variant="ghost" size="icon" onClick={() => setCurrentDate(subMonths(currentDate, 1))} className="rounded-xl hover:bg-muted font-bold">
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div className="px-6 py-1 min-w-[180px] text-center">
            <span className="text-sm font-black uppercase tracking-widest">
              {format(currentDate, "MMMM yyyy", { locale: ptBR })}
            </span>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setCurrentDate(addMonths(currentDate, 1))} className="rounded-xl hover:bg-muted font-bold">
            <ChevronRight className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">
        {Object.entries(STATUS_MAP).map(([key, cfg]) => (
          <div key={key} className="flex items-center gap-2 bg-card/30 px-3 py-1.5 rounded-full border border-border/50">
            <div className={`h-2 w-2 rounded-full ${cfg.color}`} />
            {cfg.label}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-3">
        {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].map(d => (
          <div key={d} className="text-center text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/40 pb-2">
            {d}
          </div>
        ))}

        {days.map((day, idx) => {
          const status = getDayStatus(day);
          const cfg = status ? STATUS_MAP[status] : null;
          const isCurrentMonth = isSameMonth(day, monthStart);
          const today = isToday(day);

          return (
            <div
              key={idx}
              onClick={() => isCurrentMonth && handleDayClick(day)}
              className={`
                relative h-32 rounded-3xl border transition-all duration-300 group
                ${isCurrentMonth ? "cursor-pointer hover:border-primary/50 hover:shadow-xl hover:-translate-y-1" : "opacity-20 pointer-events-none grayscale"}
                ${today ? "border-primary/40 bg-primary/5" : "bg-card/40"}
                ${status ? "border-l-4" : ""}
                ${status === 'aprovado' ? 'border-l-emerald-500' : ''}
                ${status === 'em_revisao' ? 'border-l-amber-500' : ''}
                ${status === 'rascunho' ? 'border-l-sky-500' : ''}
                ${status === 'atrasado' ? 'border-l-red-500 bg-red-500/5' : ''}
              `}
            >
              <div className="p-4 h-full flex flex-col justify-between">
                <div className="flex justify-between items-start">
                  <span className={`text-xl font-black tracking-tighter ${today ? "text-primary" : "text-foreground"}`}>
                    {format(day, "d")}
                  </span>
                  {cfg && (
                    <cfg.icon className={`h-5 w-5 ${cfg.color.replace('bg-', 'text-')} opacity-60`} />
                  )}
                </div>

                {status && (
                  <div className="mt-auto">
                    <p className={`text-[9px] font-black uppercase tracking-widest ${cfg?.color.replace('bg-', 'text-')}`}>
                      {cfg?.label}
                    </p>
                    <div className="flex items-center gap-1 text-muted-foreground mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                       <span className="text-[9px] font-bold">Ver RDO</span>
                       <ArrowRight className="h-2 w-2" />
                    </div>
                  </div>
                )}
              </div>

              {/* Day glow effect on hover */}
              <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
            </div>
          );
        })}
      </div>

      {/* Quick Insights Footer */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
        <aside className="rounded-3xl border bg-gradient-to-br from-emerald-500/10 to-background p-6 space-y-2">
            <h4 className="text-sm font-bold">Conformidade Mensal</h4>
            <div className="text-3xl font-black tracking-tighter text-emerald-400">
                {statusList?.filter(s => s.status === 'aprovado').length || 0} / {days.filter(d => isSameMonth(d, monthStart)).length}
            </div>
            <p className="text-xs text-muted-foreground">Dias com RDO aprovado e validado juridicamente.</p>
        </aside>
        
        <aside className="rounded-3xl border bg-gradient-to-br from-red-500/10 to-background p-6 space-y-2">
            <h4 className="text-sm font-bold">Pendências Críticas</h4>
            <div className="text-3xl font-black tracking-tighter text-red-400">
                {statusList?.filter(s => s.status === 'atrasado' || s.status === 'em_revisao').length || 0}
            </div>
            <p className="text-xs text-muted-foreground">Relatórios que necessitam de intervenção ou submissão.</p>
        </aside>

        <aside className="rounded-3xl border bg-card/60 p-6 space-y-4 flex flex-col justify-center border-dashed">
            <div className="flex items-center gap-3">
                <Search className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm font-bold italic tracking-tight">Dica de Gestão:</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
                Mantenha seu calendário <span className="text-emerald-400 font-bold">verde</span>. Relatórios em atraso podem gerar multas contratuais e perda de histórico de obra.
            </p>
        </aside>
      </div>
    </div>
  );
}
