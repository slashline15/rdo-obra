import { Link } from "@tanstack/react-router";
import { useObras } from "@/hooks/use-diario";
import { HardHat, ChevronRight } from "lucide-react";
import { format } from "date-fns";

export default function ObrasPage() {
  const { data: obras, isLoading } = useObras();
  const hoje = format(new Date(), "yyyy-MM-dd");

  if (isLoading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-6">Obras</h1>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Obras</h1>

      {!obras?.length && (
        <p className="text-muted-foreground">Nenhuma obra encontrada.</p>
      )}

      <div className="space-y-3">
        {obras?.map((obra) => (
          <Link
            key={obra.id}
            to="/obras/$obraId/diario/$data"
            params={{ obraId: String(obra.id), data: hoje }}
            className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors group"
          >
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <HardHat className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">{obra.nome}</p>
                {obra.endereco && (
                  <p className="text-sm text-muted-foreground">{obra.endereco}</p>
                )}
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
          </Link>
        ))}
      </div>
    </div>
  );
}
