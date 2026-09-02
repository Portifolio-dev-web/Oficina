const TONES = {
  emerald: "border-emerald-600 bg-emerald-950 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.25)]",
  amber: "border-amber-600 bg-amber-950 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.25)]",
  slate: "border-slate-700 bg-slate-800 text-slate-400",
  sky: "border-sky-600 bg-sky-950 text-sky-300",
};

export default function StatusBadge({ label, tone = "slate", testid }) {
  return (
    <span
      data-testid={testid}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${TONES[tone]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
