import { useEffect } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  BarChart3,
  Bot,
  CalendarCheck2,
  ClipboardList,
  FileText,
  HardHat,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import heroImage from "@/assets/hero.png";
import { useAuth } from "@/lib/auth-context";

const features = [
  {
    icon: MessageSquareText,
    title: "Mensageria de obra",
    text: "WhatsApp e Telegram entram no mesmo fluxo, com escolha guiada e persistência durável.",
  },
  {
    icon: FileText,
    title: "HTML e PDF",
    text: "O RDO sai pronto para envio, impressão e assinatura, sem retrabalho manual.",
  },
  {
    icon: ShieldCheck,
    title: "Trilha auditável",
    text: "Tudo que é registrado fica rastreado no banco, do ajuste fino ao fechamento do dia.",
  },
  {
    icon: Bot,
    title: "Inteligência útil",
    text: "O motor entende mensagem solta, conclui atividade certa e reduz decisões erradas.",
  },
];

const steps = [
  {
    icon: HardHat,
    title: "1. Registra",
    text: "A equipe fala, escreve ou envia foto da frente de obra.",
  },
  {
    icon: Workflow,
    title: "2. Processa",
    text: "O orquestrador classifica, busca e encaixa o dado no módulo certo.",
  },
  {
    icon: CalendarCheck2,
    title: "3. Entrega",
    text: "O sistema gera o diário, exporta HTML/PDF e deixa pronto para apresentação.",
  },
];

const proofPoints = [
  { icon: MessageSquareText, text: "Entrada por WhatsApp, Telegram e painel" },
  { icon: FileText, text: "Exportação HTML e PDF do RDO" },
  { icon: BarChart3, text: "Dashboard com KPIs executivos" },
  { icon: ShieldCheck, text: "Busca semântica para concluir atividade certa" },
];

export default function PresentationPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate({ to: "/obras" });
    }
  }, [loading, navigate, user]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(255,145,77,0.14),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(32,120,255,0.12),_transparent_28%),linear-gradient(180deg,var(--background),var(--background))]">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-8rem] top-[-6rem] h-72 w-72 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute bottom-[-8rem] right-[-4rem] h-80 w-80 rounded-full bg-sky-500/10 blur-3xl" />
      </div>

      <main className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary shadow-sm">
              <ClipboardList className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">RDO Digital</p>
              <p className="text-xs text-muted-foreground">RDO por voz, WhatsApp e PDF no mesmo fluxo</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="inline-flex h-10 items-center justify-center rounded-lg border border-border bg-card px-4 text-sm font-medium shadow-sm transition-colors hover:bg-muted"
            >
              Entrar
            </Link>
            <Link
              to="/login"
              className="inline-flex h-10 items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
            >
              Ver painel <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        </header>

        <section className="grid flex-1 items-center gap-10 py-10 lg:grid-cols-[1.08fr_0.92fr] lg:py-14">
          <div className="space-y-7">
            <div className="inline-flex items-center gap-2 rounded-full border bg-card/80 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Beta em operação
            </div>

            <div className="space-y-5">
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl lg:text-6xl">
                Diário de obra que transforma mensagem solta em RDO apresentável.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
                O canteiro registra por áudio, texto ou foto. O sistema organiza, busca a atividade certa, fecha o
                diário e exporta HTML/PDF com rastreabilidade. É o mínimo certo para vender sem improviso.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                to="/login"
                className="inline-flex h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
              >
                Entrar no painel
              </Link>
              <a
                href="#o-que-entrega"
                className="inline-flex h-11 items-center justify-center rounded-lg border border-border bg-card px-5 text-sm font-medium shadow-sm transition-colors hover:bg-muted"
              >
                O que entrega
              </a>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {proofPoints.map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.text} className="flex items-center gap-3 rounded-2xl border bg-card/80 p-4 shadow-sm backdrop-blur">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                    <p className="text-sm text-foreground/90">{item.text}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="relative">
            <div className="absolute -inset-2 rounded-[2rem] bg-gradient-to-br from-primary/10 via-transparent to-sky-500/10 blur-2xl" />
            <div className="relative rounded-[2rem] border bg-card/85 p-4 shadow-[0_24px_90px_rgba(0,0,0,0.16)] backdrop-blur">
              <div className="overflow-hidden rounded-[1.4rem] border bg-[#0f1115]">
                <img
                  src={heroImage}
                  alt="Ilustração do produto RDO Digital"
                  className="h-[240px] w-full object-cover sm:h-[300px]"
                />
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                {[
                  { value: "WhatsApp", label: "entrada principal" },
                  { value: "HTML + PDF", label: "saída comercial" },
                  { value: "Auditável", label: "pronto para cliente" },
                ].map((metric) => (
                  <div key={metric.label} className="rounded-2xl border bg-background/80 p-4">
                    <p className="text-sm font-semibold">{metric.value}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{metric.label}</p>
                  </div>
                ))}
              </div>

              <div className="mt-4 rounded-2xl border bg-muted/40 p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <BarChart3 className="h-4 w-4 text-primary" />
                  Fluxo de entrega
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  {steps.map((step) => {
                    const Icon = step.icon;
                    return (
                      <div key={step.title} className="rounded-xl border bg-card p-3">
                        <Icon className="h-4 w-4 text-primary" />
                        <p className="mt-2 text-sm font-semibold">{step.title}</p>
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">{step.text}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="o-que-entrega" className="pb-8">
          <div className="mb-4 flex items-center gap-2">
            <div className="h-1.5 w-10 rounded-full bg-primary" />
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">O que entrega</p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div key={feature.title} className="rounded-2xl border bg-card/80 p-5 shadow-sm backdrop-blur">
                  <Icon className="h-5 w-5 text-primary" />
                  <h2 className="mt-4 text-base font-semibold">{feature.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{feature.text}</p>
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
