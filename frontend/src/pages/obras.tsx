import { Link } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useObras } from "@/hooks/use-diario";
import { HardHat, MapPin, Plus, X, CalendarRange } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { apiPost } from "@/lib/api";
import { toast } from "sonner";
import { useState } from "react";

export default function ObrasPage() {
  const { data: obras, isLoading } = useObras();
  const queryClient = useQueryClient();
  const [showNova, setShowNova] = useState(false);
  const [nomeNova, setNomeNova] = useState("");
  const hoje = format(new Date(), "yyyy-MM-dd");
  const hojeFormatado = format(new Date(), "EEEE, dd 'de' MMMM", { locale: ptBR });

  async function handleCriarObra() {
    if (!nomeNova.trim()) {
      toast.error("Informe o nome da obra");
      return;
    }
    try {
      await apiPost("/obras", { nome: nomeNova });
      setShowNova(false);
      setNomeNova("");
      queryClient.invalidateQueries({ queryKey: ["obras"] });
    } catch (err) {
      toast.error("Erro ao criar obra");
    }
  }

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="mb-8 font-black uppercase tracking-widest opacity-20">Obras</div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 rounded-3xl bg-card/40 border animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
           <div className="text-primary font-bold uppercase tracking-[0.2em] text-[10px] mb-1">Portfólio Ativo</div>
           <h1 className="text-4xl font-black tracking-tighter">Canteiros de Obra</h1>
           <p className="text-muted-foreground text-sm font-medium capitalize mt-1">{hojeFormatado}</p>
        </div>
        <button
          onClick={() => setShowNova(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-primary/10 text-primary border border-primary/20 text-xs font-bold uppercase tracking-widest hover:bg-primary/20 transition-all active:scale-95 shadow-lg shadow-primary/5"
        >
          <Plus className="h-4 w-4" />
          Cadastrar Obra
        </button>
      </div>

      {!obras?.length && (
        <div className="text-center py-32 rounded-3xl border border-dashed border-border/60 bg-card/20 backdrop-blur-sm">
          <HardHat className="h-12 w-12 mx-auto mb-4 opacity-10 text-primary" />
          <p className="text-sm font-bold uppercase tracking-widest opacity-30">Nenhum canteiro ativo encontrado.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {obras?.map((obra) => (
          <div key={obra.id} className="group relative border rounded-[2rem] bg-card/40 p-6 backdrop-blur-sm hover:border-primary/50 transition-all duration-300 hover:shadow-2xl hover:shadow-primary/10 hover:-translate-y-1 flex flex-col h-64 overflow-hidden">
            {/* Top row */}
            <div className="flex items-center justify-between mb-4">
              <div className="h-14 w-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20 group-hover:scale-110 transition-transform duration-500 shadow-inner shadow-primary/5">
                <HardHat className="h-6 w-6" />
              </div>
              <div className="flex flex-col items-end">
                <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/30">ID #{obra.id}</span>
                <span className={`mt-1 text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full border ${obra.status === 'ativo' ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/5' : 'border-muted text-muted-foreground'}`}>
                    {obra.status || 'On-Track'}
                </span>
              </div>
            </div>

            {/* Info */}
            <div className="flex-1 space-y-2">
              <h3 className="font-black text-xl tracking-tight leading-tight group-hover:text-primary transition-colors line-clamp-2">
                {obra.nome}
              </h3>
              {obra.endereco && (
                <p className="text-xs text-muted-foreground font-medium flex items-start gap-1.5 opacity-60 group-hover:opacity-100 transition-opacity italic">
                  <MapPin className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                  {obra.endereco}
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Link
                to="/obras/$obraId/diario/$data"
                params={{ obraId: String(obra.id), data: hoje }}
                className="flex-1 inline-flex items-center justify-center h-12 px-6 rounded-2xl bg-primary text-xs font-black uppercase tracking-widest text-primary-foreground hover:brightness-110 active:scale-95 transition-all shadow-xl shadow-primary/20"
              >
                Abrir Diário
              </Link>
              <Link
                to="/obras/$obraId/historico"
                params={{ obraId: String(obra.id) }}
                className="inline-flex items-center justify-center h-12 w-14 rounded-2xl border bg-muted/20 text-muted-foreground hover:bg-muted hover:text-foreground active:scale-95 transition-all"
                title="Histórico Completo"
              >
                <CalendarRange className="h-4 w-4" />
              </Link>
            </div>

            {/* Decorative BG element */}
            <div className="absolute top-0 right-0 h-32 w-32 bg-primary/5 rounded-full -mr-16 -mt-16 blur-3xl group-hover:bg-primary/10 transition-colors" />
          </div>
        ))}
      </div>

      {/* Modal */}
      {showNova && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-background/80 backdrop-blur-md" onClick={() => setShowNova(false)} />
          <div className="relative w-full max-w-md rounded-[2.5rem] border bg-card p-8 shadow-2xl animate-in zoom-in duration-300">
            <div className="flex items-center justify-between mb-8">
               <div className="space-y-1">
                 <h2 className="text-2xl font-black tracking-tight">Nova Unidade</h2>
                 <p className="text-xs text-muted-foreground font-bold uppercase tracking-widest">Registrar canteiro no sistema</p>
               </div>
               <button onClick={() => setShowNova(false)} className="p-2 rounded-xl hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors">
                 <X className="h-5 w-5" />
               </button>
            </div>
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground px-1">Identificação da Obra</label>
                <input
                  type="text"
                  value={nomeNova}
                  onChange={(e) => setNomeNova(e.target.value)}
                  placeholder="Ex: Edifício Corporate Center"
                  className="w-full h-12 rounded-2xl border bg-background px-4 text-sm font-bold placeholder:font-medium focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
                  autoFocus
                />
              </div>
              <div className="flex gap-3">
                 <button
                  onClick={() => setShowNova(false)}
                  className="flex-1 h-12 rounded-2xl border text-xs font-black uppercase tracking-widest hover:bg-muted transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleCriarObra}
                  className="flex-1 h-12 rounded-2xl bg-primary text-primary-foreground text-xs font-black uppercase tracking-widest hover:brightness-110 shadow-xl shadow-primary/20 transition-all"
                >
                  Confirmar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
