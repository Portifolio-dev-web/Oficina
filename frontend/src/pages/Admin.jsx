import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Loader2, Car, Clock, CheckCircle2, Users, Wrench, ChevronLeft, ChevronRight,
  MessageSquareText, CalendarDays, ClipboardList,
} from "lucide-react";
import { toast } from "sonner";
import { getAdminOverview, toggleMechanic, updateStage } from "@/lib/api";
import { STAGES, formatBRL } from "@/constants/data";
import StatusBadge from "@/components/StatusBadge";

const stageTone = (i) => (i === 0 ? "sky" : i === 4 ? "emerald" : "amber");

export default function Admin() {
  const [data, setData] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(() => getAdminOverview().then(setData).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);

  const changeStage = async (appt, stage) => {
    setBusyId(appt.id);
    try {
      const updated = await updateStage(appt.id, stage);
      if (updated.statusIndex !== appt.statusIndex) {
        const last = updated.smsLogs[updated.smsLogs.length - 1];
        toast(`[Simulação SMS → ${updated.user.name.split(" ")[0]}] ${last.message}`, {
          icon: <MessageSquareText className="h-4 w-4" />,
          duration: 8000,
        });
      }
      await load();
    } catch {
      toast.error("Falha ao atualizar o status.");
    } finally {
      setBusyId(null);
    }
  };

  const handleToggleMechanic = async (m) => {
    await toggleMechanic(m.id).catch(() => {});
    load();
  };

  if (!data) {
    return (
      <main className="flex items-center justify-center py-40">
        <Loader2 data-testid="admin-loading" className="h-8 w-8 animate-spin text-emerald-400" />
      </main>
    );
  }

  const { stats, appointments, mechanics, services } = data;
  const kpis = [
    { testid: "kpi-em-manutencao", label: "Em manutenção", value: stats.emManutencao, icon: Wrench, cls: "text-amber-400 bg-amber-500/15" },
    { testid: "kpi-aguardando", label: "Aguardando entrada", value: stats.aguardando, icon: Clock, cls: "text-sky-400 bg-sky-500/15" },
    { testid: "kpi-prontos", label: "Prontos p/ retirada", value: stats.prontos, icon: CheckCircle2, cls: "text-emerald-400 bg-emerald-500/15" },
    { testid: "kpi-mecanicos", label: "Mecânicos disponíveis", value: `${stats.mecanicosDisponiveis}/${stats.mecanicosTotal}`, icon: Users, cls: "text-emerald-400 bg-emerald-500/15" },
    { testid: "kpi-servicos", label: "Serviços agendados", value: appointments.reduce((a, x) => a + x.services.length, 0), icon: ClipboardList, cls: "text-slate-300 bg-slate-500/15" },
  ];

  return (
    <main data-testid="admin-dashboard" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-display text-3xl font-extrabold tracking-tight md:text-4xl">Painel da Oficina</h1>
        <p className="mt-2 text-sm text-slate-400">
          Gerencie os veículos, atualize etapas (com envio automático de SMS) e acompanhe a equipe.
        </p>
      </motion.div>

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
        {kpis.map((k, i) => (
          <motion.div
            key={k.testid}
            data-testid={k.testid}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="rounded-2xl border border-slate-700 bg-slate-800/60 p-5"
          >
            <span className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl ${k.cls}`}>
              <k.icon className="h-5 w-5" />
            </span>
            <div className="font-display text-2xl font-extrabold">{k.value}</div>
            <div className="text-xs text-slate-400">{k.label}</div>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <h2 className="mb-4 flex items-center gap-2 font-display text-xl font-bold">
            <Car className="h-5 w-5 text-emerald-400" />
            Veículos na oficina ({appointments.length})
          </h2>
          <div className="space-y-3">
            {appointments.map((a) => (
              <motion.div
                key={a.id}
                data-testid="admin-vehicle-card"
                layout
                className="rounded-2xl border border-slate-700 bg-slate-800/60 p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-lg border border-slate-600 bg-slate-900 px-2 py-0.5 font-mono2 text-xs font-bold tracking-wider text-slate-200">
                        {a.vehicle.plate || "SEM PLACA"}
                      </span>
                      <h3 className="font-display text-base font-bold">
                        {a.vehicle.make} {a.vehicle.model}
                      </h3>
                      <StatusBadge label={a.status} tone={stageTone(a.statusIndex)} />
                    </div>
                    <p className="mt-1.5 text-xs text-slate-400">
                      {a.user.name} · {a.user.phone}
                    </p>
                    <p className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <CalendarDays className="h-3.5 w-3.5" />
                        {a.date.split("-").reverse().join("/")} · {a.time} ({a.period})
                      </span>
                      <span className="font-mono2">{a.id}</span>
                    </p>
                    <p className="mt-2 text-xs text-slate-400">
                      <span className="font-semibold text-slate-300">Serviços:</span>{" "}
                      {a.services.map((s) => `${s.name} (${s.duration})`).join(", ")}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      data-testid={`btn-admin-regress-${a.id}`}
                      onClick={() => changeStage(a, a.statusIndex - 1)}
                      disabled={busyId === a.id || a.statusIndex <= 0}
                      className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-600 text-slate-300 transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-30"
                      title="Voltar etapa"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <button
                      data-testid={`btn-admin-advance-${a.id}`}
                      onClick={() => changeStage(a, a.statusIndex + 1)}
                      disabled={busyId === a.id || a.statusIndex >= STAGES.length - 1}
                      className="flex h-9 items-center gap-1.5 rounded-lg bg-emerald-500 px-3.5 text-xs font-bold text-white transition-colors hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-30"
                    >
                      {busyId === a.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <ChevronRight className="h-4 w-4" />}
                      Avançar + SMS
                    </button>
                    <Link
                      data-testid={`btn-admin-track-${a.id}`}
                      to={`/rastreio/${a.id}`}
                      className="flex h-9 items-center rounded-lg border border-slate-600 px-3 text-xs font-semibold text-slate-300 transition-colors hover:bg-slate-700"
                    >
                      Rastreio
                    </Link>
                  </div>
                </div>
                <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-700">
                  <motion.div
                    className="h-full rounded-full bg-emerald-500"
                    initial={false}
                    animate={{ width: `${((a.statusIndex + 1) / STAGES.length) * 100}%` }}
                    transition={{ type: "spring", damping: 25, stiffness: 120 }}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        <aside className="space-y-6">
          <section className="rounded-2xl border border-slate-700 bg-slate-800/60 p-5">
            <h2 className="mb-4 flex items-center gap-2 font-display text-lg font-bold">
              <Users className="h-5 w-5 text-emerald-400" />
              Equipe de mecânicos
            </h2>
            <div className="space-y-2.5">
              {mechanics.map((m) => (
                <div
                  key={m.id}
                  data-testid="mechanic-item"
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-700/70 bg-slate-900/40 px-3.5 py-3"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{m.name}</div>
                    <div className="truncate text-[11px] text-slate-500">{m.specialty}</div>
                  </div>
                  <button
                    data-testid={`btn-toggle-mechanic-${m.id}`}
                    onClick={() => handleToggleMechanic(m)}
                    className={`shrink-0 rounded-full border px-3 py-1 text-[11px] font-bold transition-all ${
                      m.available
                        ? "border-emerald-600 bg-emerald-950 text-emerald-300"
                        : "border-slate-600 bg-slate-800 text-slate-400 hover:border-slate-500"
                    }`}
                  >
                    {m.available ? "Disponível" : "Ocupado"}
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-700 bg-slate-800/60 p-5">
            <h2 className="mb-4 flex items-center gap-2 font-display text-lg font-bold">
              <ClipboardList className="h-5 w-5 text-amber-400" />
              Serviços a realizar
            </h2>
            <div className="space-y-2.5">
              {services.map((s) => (
                <div
                  key={s.name}
                  data-testid="service-agenda-item"
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-700/70 bg-slate-900/40 px-3.5 py-3"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{s.name}</div>
                    <div className="flex items-center gap-1 text-[11px] text-slate-500">
                      <Clock className="h-3 w-3" /> Tempo médio: {s.duration}
                    </div>
                  </div>
                  <span className="shrink-0 rounded-full bg-amber-950 px-2.5 py-1 font-mono2 text-xs font-bold text-amber-300">
                    ×{s.count}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}
