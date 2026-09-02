import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

const MONTHS = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
const WEEKDAYS = ["D","S","T","Q","Q","S","S"];

const iso = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export default function MiniCalendar({ value, onChange }) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const [cursor, setCursor] = useState(new Date(today.getFullYear(), today.getMonth(), 1));

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells = [];
  for (let i = 0; i < firstWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));

  const canPrev = year > today.getFullYear() || (year === today.getFullYear() && month > today.getMonth());

  return (
    <div data-testid="calendar-booking-date" className="rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
      <div className="mb-3 flex items-center justify-between">
        <button
          data-testid="btn-calendar-prev"
          onClick={() => canPrev && setCursor(new Date(year, month - 1, 1))}
          disabled={!canPrev}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-700 hover:text-slate-200 disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="font-display text-sm font-semibold">
          {MONTHS[month]} <span className="text-slate-400">{year}</span>
        </span>
        <button
          data-testid="btn-calendar-next"
          onClick={() => setCursor(new Date(year, month + 1, 1))}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-700 hover:text-slate-200"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1">
        {WEEKDAYS.map((w, i) => (
          <div key={i} className="pb-1 text-center text-[10px] font-bold uppercase text-slate-500">{w}</div>
        ))}
        {cells.map((d, i) => {
          if (!d) return <div key={`e${i}`} />;
          const disabled = d < today;
          const selected = value === iso(d);
          return (
            <button
              key={iso(d)}
              data-testid={`calendar-day-${iso(d)}`}
              disabled={disabled}
              onClick={() => onChange(iso(d))}
              className={`h-9 rounded-lg text-sm font-medium transition-all ${
                selected
                  ? "bg-emerald-500 text-white shadow-[0_0_14px_rgba(16,185,129,0.45)]"
                  : disabled
                    ? "cursor-not-allowed text-slate-700"
                    : "text-slate-300 hover:bg-slate-700"
              }`}
            >
              {d.getDate()}
            </button>
          );
        })}
      </div>
    </div>
  );
}
