import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  CalendarCheck, Radar, MessageSquareText, Wrench, ShieldCheck, Clock, ChevronRight, Sparkles,
} from "lucide-react";
import { useSession } from "@/lib/session";
import { SERVICE_CATEGORIES } from "@/constants/data";

const fadeUp = {
  initial: { opacity: 0, y: 28 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.55 },
};

export default function Home() {
  const { session, openOnboarding } = useSession();
  const navigate = useNavigate();
  const start = () => (session ? navigate("/agendar") : openOnboarding());

  return (
    <main>
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute -left-40 top-0 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
        <div className="pointer-events-none absolute -right-32 bottom-0 h-80 w-80 rounded-full bg-amber-500/10 blur-3xl" />
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 md:py-24 lg:grid-cols-2 lg:px-8">
          <motion.div initial={{ opacity: 0, y: 32 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-emerald-600/50 bg-emerald-950/60 px-4 py-1.5 text-xs font-semibold text-emerald-300">
              <Sparkles className="h-3.5 w-3.5" />
              Oficina conectada · rastreio em tempo real
            </span>
            <h1 className="font-display text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
              Seu carro em boas mãos,{" "}
              <span className="text-emerald-400">do agendamento à retirada</span>
            </h1>
            <p className="mt-6 max-w-lg text-base leading-relaxed text-slate-400">
              Agende serviços em minutos e acompanhe cada etapa do reparo com atualizações
              de status e notificações por SMS — tudo em um só lugar.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                data-testid="btn-hero-agendar"
                onClick={start}
                className="group flex items-center gap-2 rounded-full bg-emerald-500 px-7 py-3.5 text-sm font-bold text-white shadow-[0_0_28px_rgba(16,185,129,0.4)] transition-all hover:bg-emerald-600 hover:shadow-[0_0_36px_rgba(16,185,129,0.55)]"
              >
                Agendar serviço
                <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </button>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Clock className="h-4 w-4 text-amber-400" />
                Confirmação em menos de 1 minuto
              </div>
            </div>
            <div className="mt-10 flex gap-8 border-t border-slate-800 pt-8">
              {[["12k+", "veículos atendidos"], ["4.9", "avaliação média"], ["98%", "entregues no prazo"]].map(([v, l]) => (
                <div key={l}>
                  <div className="font-display text-2xl font-extrabold text-slate-100">{v}</div>
                  <div className="text-xs text-slate-500">{l}</div>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.15 }}
            className="relative"
          >
            <div className="overflow-hidden rounded-3xl border border-slate-700 shadow-2xl shadow-slate-950/60">
              <img
                src="https://images.unsplash.com/photo-1615906655593-ad0386982a0f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTF8MHwxfHNlYXJjaHwxfHxjYXIlMjBtZWNoYW5pYyUyMHJlcGFpciUyMHdvcmtzaG9wJTIwYXV0b21vdGl2ZSUyMHNlcnZpY2V8ZW58MHx8fHwxNzg4Mzg3MzM0fDA&ixlib=rb-4.1.0&q=85"
                alt="Mecânico trabalhando em veículo"
                className="h-full w-full object-cover"
              />
            </div>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="absolute -bottom-5 -left-3 flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-800/95 px-4 py-3 shadow-xl backdrop-blur sm:-left-8"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
                <Radar className="h-5 w-5" />
              </span>
              <div>
                <div className="text-xs font-bold text-slate-200">Rastreio ao vivo</div>
                <div className="text-[11px] text-slate-400">5 etapas + SMS em tempo real</div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <motion.div {...fadeUp} className="mb-10">
          <h2 className="font-display text-2xl font-bold tracking-tight md:text-3xl">Como funciona</h2>
          <p className="mt-2 text-sm text-slate-400">Três passos simples para cuidar do seu veículo.</p>
        </motion.div>
        <div className="grid gap-6 md:grid-cols-3">
          {[
            { icon: CalendarCheck, t: "1. Cadastre-se e agende", d: "Crie sua conta com verificação por SMS, escolha os serviços e selecione data e horário." },
            { icon: MessageSquareText, t: "2. Receba notificações", d: "A cada mudança de etapa, você recebe um SMS com a atualização do seu veículo." },
            { icon: ShieldCheck, t: "3. Acompanhe e retire", d: "Siga o rastreio ao vivo em 5 etapas e retire seu carro com garantia de qualidade." },
          ].map((s, i) => (
            <motion.div
              key={s.t}
              {...fadeUp}
              transition={{ duration: 0.5, delay: i * 0.12 }}
              className="rounded-2xl border border-slate-700 bg-slate-800/60 p-6 transition-colors hover:border-slate-600"
            >
              <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
                <s.icon className="h-6 w-6" />
              </span>
              <h3 className="font-display text-lg font-semibold">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{s.d}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
        <motion.div {...fadeUp} className="mb-10 flex items-end justify-between">
          <div>
            <h2 className="font-display text-2xl font-bold tracking-tight md:text-3xl">Nossos serviços</h2>
            <p className="mt-2 text-sm text-slate-400">Catálogo completo para o seu veículo.</p>
          </div>
          <button
            data-testid="btn-catalog-agendar"
            onClick={start}
            className="hidden items-center gap-1.5 text-sm font-semibold text-emerald-400 transition-colors hover:text-emerald-300 sm:flex"
          >
            Ver catálogo completo <ChevronRight className="h-4 w-4" />
          </button>
        </motion.div>
        <div className="grid gap-6 md:grid-cols-3">
          {SERVICE_CATEGORIES.map((c, i) => (
            <motion.div
              key={c.id}
              {...fadeUp}
              transition={{ duration: 0.5, delay: i * 0.12 }}
              className="rounded-2xl border border-slate-700 bg-slate-800/60 p-6"
            >
              <div className="mb-4 flex items-center gap-2">
                <Wrench className="h-4 w-4 text-amber-400" />
                <h3 className="font-display text-base font-semibold">{c.label}</h3>
              </div>
              <ul className="space-y-2.5">
                {c.services.map((s) => (
                  <li key={s.id} className="flex items-center justify-between text-sm">
                    <span className="text-slate-300">{s.name}</span>
                    <span className="font-mono2 text-xs text-slate-500">{s.duration}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </section>

      <footer className="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
        AutoFix Pro — Oficina Conectada · Demonstração com dados simulados
      </footer>
    </main>
  );
}
