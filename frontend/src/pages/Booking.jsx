import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  Droplets, Waves, ClipboardCheck, Disc3, Cog, Gauge, Wrench, Cpu, Zap, Snowflake,
  Check, CalendarDays, Clock, Loader2, MessageSquareText, UserRound,
} from "lucide-react";
import { toast } from "sonner";
import { useSession } from "@/lib/session";
import { createAppointment } from "@/lib/api";
import { SERVICE_CATEGORIES, TIME_SLOTS, formatBRL } from "@/constants/data";
import MiniCalendar from "@/components/MiniCalendar";

const ICONS = {
  droplets: Droplets, waves: Waves, clipboard: ClipboardCheck, disc: Disc3, cog: Cog,
  gauge: Gauge, wrench: Wrench, cpu: Cpu, zap: Zap, snowflake: Snowflake,
};

export default function Booking() {
  const { session, openOnboarding } = useSession();
  const navigate = useNavigate();
  const scheduleRef = useRef(null);

  const [cat, setCat] = useState("preventiva");
  const [selected, setSelected] = useState([]);
  const [date, setDate] = useState("");
  const [period, setPeriod] = useState("manha");
  const [time, setTime] = useState("");
  const [loading, setLoading] = useState(false);

  const activeCat = SERVICE_CATEGORIES.find((c) => c.id === cat);
  const allServices = SERVICE_CATEGORIES.flatMap((c) => c.services);
  const selectedServices = useMemo(
    () => allServices.filter((s) => selected.includes(s.id)),
    [selected, allServices]
  );
  const total = selectedServices.reduce((acc, s) => acc + s.price, 0);
  const ready = selected.length > 0 && date && time;

  if (!session) {
    return (
      <main className="mx-auto flex max-w-md flex-col items-center px-4 py-28 text-center">
        <span className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-400">
          <UserRound className="h-8 w-8" />
        </span>
        <h1 className="font-display text-2xl font-bold">Identifique-se para agendar</h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          Crie sua conta em segundos com verificação por SMS e cadastre seu veículo para começar.
        </p>
        <button
          data-testid="btn-booking-login"
          onClick={openOnboarding}
          className="mt-8 rounded-full bg-emerald-500 px-8 py-3 text-sm font-bold text-white transition-colors hover:bg-emerald-600"
        >
          Entrar / Cadastrar
        </button>
      </main>
    );
  }

  const toggle = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const handleConfirm = async () => {
    setLoading(true);
    try {
      const payload = {
        user: session.user,
        vehicle: session.user.vehicle,
        services: selectedServices.map((s) => ({ id: s.id, name: s.name, price: s.price, duration: s.duration })),
        date,
        time,
        period: TIME_SLOTS[period].label,
      };
      const appt = await createAppointment(payload);
      toast.success("Agendamento confirmado!");
      const carro = `${appt.vehicle.make} ${appt.vehicle.model}`;
      toast(`[Simulação SMS] Olá ${appt.user.name.split(" ")[0]}, seu agendamento para o ${carro} foi confirmado. Link: /rastreio/${appt.id}`, {
        icon: <MessageSquareText className="h-4 w-4" />,
        duration: 9000,
      });
      navigate(`/rastreio/${appt.id}`);
    } catch {
      toast.error("Não foi possível concluir o agendamento.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-10 pb-40 sm:px-6 lg:px-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-display text-3xl font-extrabold tracking-tight md:text-4xl">Agendar serviço</h1>
        <p className="mt-2 text-sm text-slate-400">
          {session.user.vehicle.make} {session.user.vehicle.model}
          {session.user.vehicle.plate ? ` · ${session.user.vehicle.plate}` : ""} — selecione os serviços desejados.
        </p>
      </motion.div>

      <div className="mb-6 flex flex-wrap gap-2">
        {SERVICE_CATEGORIES.map((c) => (
          <button
            key={c.id}
            data-testid={c.testid}
            onClick={() => setCat(c.id)}
            className={`rounded-full px-4 py-2 text-xs font-semibold transition-all sm:text-sm ${
              cat === c.id
                ? "bg-emerald-500 text-white shadow-[0_0_16px_rgba(16,185,129,0.4)]"
                : "border border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-500"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={cat}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.22 }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {activeCat.services.map((s) => {
            const Icon = ICONS[s.icon];
            const active = selected.includes(s.id);
            return (
              <button
                key={s.id}
                data-testid="card-service-item"
                data-service-id={s.id}
                onClick={() => toggle(s.id)}
                className={`group relative rounded-2xl border p-5 text-left transition-all ${
                  active
                    ? "border-emerald-500 bg-emerald-950/40 shadow-[0_0_20px_rgba(16,185,129,0.2)]"
                    : "border-slate-700 bg-slate-800/60 hover:border-slate-500"
                }`}
              >
                {active && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute right-4 top-4 flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500"
                  >
                    <Check className="h-3.5 w-3.5 text-white" />
                  </motion.span>
                )}
                <span className={`mb-4 flex h-11 w-11 items-center justify-center rounded-xl transition-colors ${active ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-700/60 text-slate-300"}`}>
                  <Icon className="h-5 w-5" />
                </span>
                <h3 className="font-display text-base font-semibold">{s.name}</h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">{s.desc}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="font-mono2 text-sm font-semibold text-emerald-400">{formatBRL(s.price)}</span>
                  <span className="text-xs text-slate-500">{s.duration}</span>
                </div>
              </button>
            );
          })}
        </motion.div>
      </AnimatePresence>

      <div ref={scheduleRef} id="agendamento" className="mt-14 scroll-mt-24">
        <h2 className="mb-6 flex items-center gap-2 font-display text-xl font-bold md:text-2xl">
          <CalendarDays className="h-5 w-5 text-emerald-400" />
          Escolha data e horário
        </h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <MiniCalendar value={date} onChange={(d) => setDate(d)} />

          <div className="rounded-2xl border border-slate-700 bg-slate-800/60 p-5">
            <div className="mb-4 flex gap-2">
              {Object.entries(TIME_SLOTS).map(([key, p]) => (
                <button
                  key={key}
                  data-testid={`btn-slot-${key}`}
                  onClick={() => { setPeriod(key); setTime(""); }}
                  className={`flex-1 rounded-xl border px-4 py-3 text-left transition-all ${
                    period === key
                      ? "border-amber-500 bg-amber-950/40 shadow-[0_0_16px_rgba(245,158,11,0.2)]"
                      : "border-slate-700 bg-slate-900/40 hover:border-slate-500"
                  }`}
                >
                  <div className={`text-sm font-bold ${period === key ? "text-amber-300" : "text-slate-200"}`}>{p.label}</div>
                  <div className="text-[11px] text-slate-500">{p.hint}</div>
                </button>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
              {TIME_SLOTS[period].slots.map((t) => (
                <button
                  key={t}
                  data-testid={`btn-time-${t.replace(":", "")}`}
                  onClick={() => setTime(t)}
                  className={`flex items-center justify-center gap-1.5 rounded-lg border py-2.5 font-mono2 text-sm transition-all ${
                    time === t
                      ? "border-emerald-500 bg-emerald-500 text-white shadow-[0_0_14px_rgba(16,185,129,0.4)]"
                      : "border-slate-700 text-slate-300 hover:border-slate-500"
                  }`}
                >
                  <Clock className="h-3.5 w-3.5" />
                  {t}
                </button>
              ))}
            </div>
            {date && (
              <p data-testid="booking-datetime-summary" className="mt-4 text-xs text-slate-400">
                Selecionado:{" "}
                <span className="font-semibold text-slate-200">
                  {date.split("-").reverse().join("/")} · {TIME_SLOTS[period].label}
                  {time ? ` · ${time}` : ""}
                </span>
              </p>
            )}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {selected.length > 0 && (
          <motion.div
            data-testid="booking-summary-bar"
            initial={{ opacity: 0, y: 60 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 60 }}
            className="fixed bottom-4 left-1/2 z-40 w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 rounded-2xl border border-slate-600 bg-slate-800/95 p-4 shadow-2xl shadow-slate-950/70 backdrop-blur-xl"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs text-slate-400">
                  {selected.length} {selected.length === 1 ? "serviço selecionado" : "serviços selecionados"}
                </div>
                <div className="font-display text-xl font-extrabold text-emerald-400">{formatBRL(total)}</div>
              </div>
              <div className="flex gap-2">
                {!ready && (
                  <button
                    data-testid="btn-proceed-booking"
                    onClick={() => scheduleRef.current?.scrollIntoView({ behavior: "smooth" })}
                    className="rounded-full border border-amber-500/60 px-5 py-2.5 text-sm font-semibold text-amber-300 transition-colors hover:bg-amber-950/50"
                  >
                    Escolher data e hora
                  </button>
                )}
                <button
                  data-testid="btn-confirm-booking"
                  disabled={!ready || loading}
                  onClick={handleConfirm}
                  className="flex items-center gap-2 rounded-full bg-emerald-500 px-6 py-2.5 text-sm font-bold text-white transition-all hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Confirmar agendamento
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
