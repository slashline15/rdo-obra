import { useState, type ElementType } from "react";
import { marked } from "marked";
import {
  BookOpenText,
  Bot,
  ClipboardList,
  Database,
  FileText,
  ShieldCheck,
  Trash2,
  UserPlus,
} from "lucide-react";
import overviewMd from "@/content/wiki/visao-geral.md?raw";
import accessMd from "@/content/wiki/niveis-de-acesso.md?raw";
import softDeleteMd from "@/content/wiki/soft-delete.md?raw";
import fluxoRdoMd from "@/content/wiki/fluxo-rdo.md?raw";
import usoIaMd from "@/content/wiki/uso-ia.md?raw";
import bancoDadosMd from "@/content/wiki/banco-de-dados.md?raw";
import convitesMd from "@/content/wiki/convites-acesso.md?raw";

type DocEntry = {
  slug: string;
  title: string;
  description: string;
  icon: ElementType;
  content: string;
};

const DOCS: DocEntry[] = [
  {
    slug: "visao-geral",
    title: "Visão Geral",
    description: "Contexto desta base técnica e das próximas decisões arquiteturais.",
    icon: BookOpenText,
    content: overviewMd,
  },
  {
    slug: "niveis-de-acesso",
    title: "Níveis de Acesso",
    description: "Definição dos níveis 1, 2 e 3, escopo por obra e convites.",
    icon: ShieldCheck,
    content: accessMd,
  },
  {
    slug: "soft-delete",
    title: "Soft Delete",
    description: "Como funciona a exclusão lógica do diário e a lixeira do admin.",
    icon: Trash2,
    content: softDeleteMd,
  },
  {
    slug: "fluxo-rdo",
    title: "Fluxo do RDO",
    description: "Do preenchimento do dia à aprovação do relatório.",
    icon: ClipboardList,
    content: fluxoRdoMd,
  },
  {
    slug: "uso-ia",
    title: "Uso de IA",
    description: "Onde a IA ajuda e onde a decisão continua humana.",
    icon: Bot,
    content: usoIaMd,
  },
  {
    slug: "banco-de-dados",
    title: "Mapa das Informações",
    description: "Como obras, usuários e diários se conectam.",
    icon: Database,
    content: bancoDadosMd,
  },
  {
    slug: "convites-acesso",
    title: "Convites e Acesso",
    description: "Entrada de novos usuários, níveis e revogação.",
    icon: UserPlus,
    content: convitesMd,
  },
];

function renderMarkdown(markdown: string) {
  return marked.parse(markdown, { async: false });
}

export default function DocsPage() {
  const [selectedSlug, setSelectedSlug] = useState(DOCS[0].slug);
  const selected = DOCS.find((doc) => doc.slug === selectedSlug) ?? DOCS[0];

  return (
    <div className="p-8">
      <div className="mb-8 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Helper Técnico</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Fonte única de verdade para acesso, operação, auditoria e definições estruturais do produto.
          </p>
        </div>
        <div className="rounded-2xl border bg-card px-4 py-3 text-sm">
          <p className="font-medium">Wiki operacional</p>
          <p className="text-xs text-muted-foreground mt-1">
            Consulte antes de propor novos módulos de negócio.
          </p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="space-y-3">
          {DOCS.map((doc) => {
            const Icon = doc.icon;
            const active = doc.slug === selected.slug;
            return (
              <button
                key={doc.slug}
                type="button"
                onClick={() => setSelectedSlug(doc.slug)}
                className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                  active ? "border-primary/30 bg-primary/10" : "bg-card hover:bg-muted/40"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl border ${active ? "border-primary/25 bg-primary/15 text-primary" : "border-border bg-muted text-muted-foreground"}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium">{doc.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{doc.description}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </aside>

        <section className="rounded-3xl border bg-card p-8">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">{selected.title}</h2>
              <p className="text-sm text-muted-foreground">{selected.description}</p>
            </div>
          </div>

          <article
            className="prose prose-sm max-w-none prose-headings:tracking-tight prose-p:text-foreground/90 prose-li:text-foreground/90 prose-strong:text-foreground prose-a:text-primary"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(selected.content) }}
          />
        </section>
      </div>
    </div>
  );
}
