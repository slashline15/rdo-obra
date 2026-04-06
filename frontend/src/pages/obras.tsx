import { Link } from "@tanstack/react-router";
import { useObras } from "@/hooks/use-diario";
import { HardHat, MapPin, ArrowRight, Plus } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

export default function ObrasPage() {
  const { data: obras, isLoading } = useObras();
  const hoje = format(new Date(), "yyyy-MM-dd");
  const hojeFormatado = format(new Date(), "EEEE, dd 'de' MMMM", { locale: ptBR });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="mb-8">
          <div className="h-7 w-40 bg-muted animate-pulse rounded mb-2" />
          <div className="h-4 w-56 bg-muted animate-pulse rounded" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Obras</h1>
          <p className="text-sm text-muted-foreground mt-1 capitalize">{hojeFormatado}</p>
        </div>
        <button className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-border text-sm text-muted-foreground hover:border-primary/50 hover:text-primary transition-colors">
          <Plus className="h-4 w-4" />
          Nova obra
        </button>
      </div>

      {!obras?.length && (
        <div className="text-center py-20 text-muted-foreground">
          <HardHat className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p>Nenhuma obra encontrada.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {obras?.map((obra) => (
          <Link
            key={obra.id}
            to="/obras/$obraId/diario/$data"
            params={{ obraId: String(obra.id), data: hoje }}
          >
            <div className="group relative border rounded-xl bg-card p-5 hover:border-primary/50 transition-all duration-200 hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-0.5 cursor-pointer h-full flex flex-col">
              {/* Ícone + seta */}
              <div className="flex items-start justify-between mb-4">
                <div className="h-11 w-11 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/15 group-hover:bg-primary/20 transition-colors">
                  <HardHat className="h-5 w-5" />
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
              </div>

              {/* Info */}
              <div className="flex-1">
                <h3 className="font-semibold text-base leading-snug group-hover:text-primary transition-colors">
                  {obra.nome}
                </h3>
                {obra.endereco && (
                  <p className="text-sm text-muted-foreground mt-1.5 flex items-start gap-1.5 line-clamp-2">
                    <MapPin className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                    {obra.endereco}
                  </p>
                )}
              </div>

              {/* Footer */}
              <div className="mt-4 pt-3 border-t border-border/60 flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Diário de hoje</span>
                <span className="text-xs font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                  Abrir →
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
