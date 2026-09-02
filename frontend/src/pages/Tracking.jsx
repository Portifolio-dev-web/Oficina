import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check, Loader2, MessageSquareText, Activity, Car, CalendarDays, Wrench, SearchX,
} from "lucide-react";
import { toast } from "sonner";
import { getTracking, updateStage } from "@/lib/api";
import { STAGES } from "@/constants/data";
import StatusBadge from "@/components/StatusBadge";
import DevControlBar from "@/components/DevControlBar";

const fmtTs = (ts) =>
  new Date(ts).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

export default function Tracking() {
  const { id } = useParams();
  const [appt, setAppt] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("status");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getTracking(id).then(setAppt).catch(() => setError("not-found"));
  }, [id]);

  const setStage = async (stage) => {
    setBusy(true);
    try {
      const updated = await updateStage(id, stage);
      const changed = updated.statusIndex !== appt.statusIndex;
      setAppt(updated);
      if (changed) {
        const last = updated.smsLogs[updated.smsLogs.length - 1];
        toast(`[Simulação SMS] ${last.message}`, {
          icon: <MessageSquareText className="h-4 w-4" />,
          duration: 8000,
        });
      }
    } catch {
      toast.error("Falha ao atualizar o status.");
    } finally {
      setBusy(false);
    }
  };

  if (error) {
    return (
      <main className="mx-auto flex max-w-md flex-col items-center px-4 py-28 text-center">
        <span className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/15 text-amber-400">
          <SearchX className="h-8 w-8" />
        </span>
        <h1 className="font-display text-2xl font-bold">Agendamento não encontrado</h1>
        <p className="mt-3 text-sm text-slate-400">
          O código <span className="font-mono2 text-slate-300">{id}</span> não corresponde a nenhum agendamento ativo.
        </p>
        <Link
          data-testid="btn-back-home"
          to="/"
          className="mt-8 rounded-full bg-emerald-500 px-8 py-3 text-sm font-bold text-white transition-colors hover:bg-emerald-600"
        >
          Voltar ao início
        </Link>
      </main>
    );
  }

  if (!appt) {
    return (
      <main className="flex items-center justify-center py-40">
        <Loader2 data-testid="tracking-loading" className="h-8 w-8 animate-spin text-emerald-400" />
      </main>
    );
  }

  const done = appt.statusIndex === STAGES.length - 1;

  return (
    <main className="mx-auto max-w-3xl px-4 py-10 pb-36 sm:px-6">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-extrabold tracking-tight">Rastreio do veículo</h1>
          <StatusBadge
            testid="tracking-status-badge"
            label={done ? "Concluído" : "Em andamento"}
            tone={done ? "emerald" : "amber"}
          />
        </div>
        <p className="font-mono2 text-xs text-slate-500">Ordem de serviço {appt.id}</p>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <div className="flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
            <Car className="h-5 w-5 shrink-0 text-emerald-400" />
            <div className="min-w-0">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Veículo</div>
              <div data-testid="tracking-vehicle" className="truncate text-sm font-semibold">
                {appt.vehicle.make} {appt.vehicle.model}
              </div>
              {appt.vehicle.plate && <div className="font-mono2 text-[11px] text-slate-500">{appt.vehicle.plate}</div>}
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
            <CalendarDays className="h-5 w-5 shrink-0 text-amber-400" />
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Agendado para</div>
              <div data-testid="tracking-datetime" className="text-sm font-semibold">
                {appt.date.split("-").reverse().join("/")} · {appt.time}
              </div>
              <div className="text-[11px] text-slate-500">{appt.period}</div>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
            <Wrench className="h-5 w-5 shrink-0 text-sky-400" />
            <div className="min-w-0">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Serviços</div>
              <div data-testid="tracking-services" className="truncate text-sm font-semibold">
                {appt.services.map((s) => s.name).join(", ")}
              </div>
              <div className="text-[11px] text-slate-500">{appt.services.length} item(ns)</div>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="mt-8 flex gap-2">
        <button
          data-testid="tab-status"
          onClick={() => setTab("status")}
          className={`flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition-all ${
            tab === "status" ? "bg-emerald-500 text-white" : "border border-slate-700 text-slate-300 hover:border-slate-500"
          }`}
        >
          <Activity className="h-4 w-4" /> Status
        </button>
        <button
          data-testid="tab-sms-feed"
          onClick={() => setTab("sms")}
          className={`flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition-all ${
            tab === "sms" ? "bg-emerald-500 text-white" : "border border-slate-700 text-slate-300 hover:border-slate-500"
          }`}
        >
          <MessageSquareText className="h-4 w-4" /> SMS
          <span className="rounded-full bg-slate-950/40 px-2 py-0.5 text-[10px] font-bold">{appt.smsLogs.length}</span>
        </button>
      </div>

      <AnimatePresence mode="wait">
        {tab === "status" ? (
          <motion.div
            key="status"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.22 }}
            data-testid="tracking-stepper"
            className="relative mt-8"
          >
            <div className="absolute bottom-8 left-[22px] top-8 w-0.5 bg-slate-700" />
            <motion.div
              className="absolute left-[22px] top-8 w-0.5 bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.6)]"
              initial={false}
              animate={{ height: `${(appt.statusIndex / (STAGES.length - 1)) * 100}%` }}
              transition={{ type: "spring", damping: 25, stiffness: 120 }}
              style={{ maxHeight: "calc(100% - 4rem)" }}
            />
            <div className="space-y-4">
              {STAGES.map((s, i) => {
                const isDone = i < appt.statusIndex;
                const isCurrent = i === appt.statusIndex;
                return (
                  <motion.div
                    key={s.name}
                    data-testid="stepper-stage-item"
                    layout
                    className={`relative flex items-start gap-4 rounded-2xl border p-4 pl-3 transition-colors ${
                      isCurrent
                        ? done
                          ? "border-emerald-600 bg-emerald-950/30"
                          : "border-amber-600/70 bg-amber-950/20"
                        : isDone
                          ? "border-slate-700 bg-slate-800/60"
                          : "border-slate-800 bg-slate-900/40"
                    }`}
                  >
                    <motion.span
                      layout
                      className={`relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 ${
                        isDone || (isCurrent && done)
                          ? "border-emerald-500 bg-emerald-500 text-white"
                          : isCurrent
                            ? "border-amber-500 bg-amber-950 text-amber-300"
                            : "border-slate-700 bg-slate-800 text-slate-500"
                      }`}
                    >
                      {isDone || (isCurrent && done) ? (
                        <Check className="h-5 w-5" />
                      ) : (
                        <span className="font-mono2 text-sm font-bold">{i + 1}</span>
                      )}
                      {isCurrent && !done && (
                        <span className="absolute inset-0 animate-ping rounded-full bg-amber-500/30" />
                      )}
                    </motion.span>
                    <div className="flex-1 pt-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className={`font-display text-sm font-bold sm:text-base ${isCurrent ? "text-slate-100" : isDone ? "text-slate-200" : "text-slate-500"}`}>
                          {s.name}
                        </h3>
                        {isCurrent && (
                          <StatusBadge
                            label={done ? "Concluído" : "Etapa atual"}
                            tone={done ? "emerald" : "amber"}
                          />
                        )}
                        {isDone && <StatusBadge label="Concluída" tone="emerald" />}
                      </div>
                      <p className={`mt-1 text-xs leading-relaxed ${isCurrent ? "text-slate-400" : "text-slate-600"}`}>
                        {s.desc}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="sms"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.22 }}
            data-testid="sms-feed-list"
            className="mt-8 space-y-3"
          >
            {[...appt.smsLogs].reverse().map((sms) => (
              <motion.div
                key={sms.id}
                initial={{ opacity: 0, x: -14 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex gap-3 rounded-2xl border border-slate-700 bg-slate-800/60 p-4"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
                  <MessageSquareText className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-slate-300">AutoFix Pro</span>
                    <span className="font-mono2 text-[11px] text-slate-500">{fmtTs(sms.timestamp)}</span>
                  </div>
                  <p className="mt-1 text-sm leading-relaxed text-slate-300">{sms.message}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <DevControlBar
        stage={appt.statusIndex}
        busy={busy}
        onAdvance={() => setStage(appt.statusIndex + 1)}
        onRegress={() => setStage(appt.statusIndex - 1)}
        onReset={() => setStage(0)}
      />
    </main>
  );
}
