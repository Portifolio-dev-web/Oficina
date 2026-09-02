import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, RotateCcw, FlaskConical } from "lucide-react";

export default function DevControlBar({ stage, busy, onAdvance, onRegress, onReset }) {
  return (
    <motion.div
      data-testid="dev-control-bar"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, type: "spring", damping: 22 }}
      className="fixed bottom-4 right-4 z-40 rounded-2xl border border-slate-700 bg-slate-800/95 p-3 shadow-2xl shadow-slate-950/60 backdrop-blur-xl"
    >
      <div className="mb-2 flex items-center gap-1.5 px-1">
        <FlaskConical className="h-3.5 w-3.5 text-amber-400" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-amber-400">Controle Demo</span>
      </div>
      <div className="flex items-center gap-2">
        <button
          data-testid="btn-demo-regress-stage"
          onClick={onRegress}
          disabled={busy || stage <= 0}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-600 text-slate-300 transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-30"
          title="Voltar etapa"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <button
          data-testid="btn-demo-advance-stage"
          onClick={onAdvance}
          disabled={busy || stage >= 4}
          className="flex h-9 items-center gap-1.5 rounded-lg bg-emerald-500 px-4 text-xs font-bold text-white transition-colors hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-30"
        >
          Avançar etapa
          <ChevronRight className="h-4 w-4" />
        </button>
        <button
          data-testid="btn-demo-reset-stage"
          onClick={onReset}
          disabled={busy || stage === 0}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-600 text-slate-300 transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-30"
          title="Reiniciar"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}
