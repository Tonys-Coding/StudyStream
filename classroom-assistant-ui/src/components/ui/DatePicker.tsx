import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

const pad = (n: number) => String(n).padStart(2, "0");
const iso = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`;
const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

function parse(value: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}

/**
 * A date field whose calendar opens ABOVE it. The browser's own date picker
 * always opens below, which at the foot of the Dashboard runs off the window.
 */
export default function DatePicker({
  id,
  value,
  onChange,
}: {
  id?: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const selected = parse(value);
  const [open, setOpen] = useState(false);
  const [view, setView] = useState(() => {
    const base = selected ?? new Date();
    return new Date(base.getFullYear(), base.getMonth(), 1);
  });
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const away = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);

    return () => {
      document.removeEventListener("mousedown", away);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  const year = view.getFullYear();
  const month = view.getMonth();
  const lead = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  const now = new Date();
  const today = iso(now.getFullYear(), now.getMonth(), now.getDate());

  const step = (by: number) => setView(new Date(year, month + by, 1));

  return (
    <div ref={root} className="relative">
      <button
        id={id}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex h-10 w-full items-center justify-between gap-2 rounded-ctl border border-line bg-sheet px-3 text-left text-body text-ink transition-colors duration-150 hover:border-ink-3"
      >
        <span className={selected ? "" : "text-ink-3"}>
          {selected
            ? selected.toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
              })
            : "No date"}
        </span>
        <CalendarDays className="size-4 shrink-0 text-ink-2" aria-hidden />
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Choose a due date"
          className="absolute bottom-full left-0 z-30 mb-2 w-72 rounded-panel border border-rule bg-sheet p-3 shadow-pop"
        >
          <div className="mb-2 flex items-center justify-between">
            <button
              type="button"
              aria-label="Previous month"
              onClick={() => step(-1)}
              className="flex size-8 items-center justify-center rounded-ctl text-ink-2 hover:bg-sheet-2"
            >
              <ChevronLeft className="size-4" aria-hidden />
            </button>
            <p className="font-serif text-body font-semibold" aria-live="polite">
              {view.toLocaleDateString(undefined, { month: "long", year: "numeric" })}
            </p>
            <button
              type="button"
              aria-label="Next month"
              onClick={() => step(1)}
              className="flex size-8 items-center justify-center rounded-ctl text-ink-2 hover:bg-sheet-2"
            >
              <ChevronRight className="size-4" aria-hidden />
            </button>
          </div>

          <div className="grid grid-cols-7 text-center text-meta text-ink-3">
            {WEEKDAYS.map((d, i) => (
              <span key={i} className="py-1">
                {d}
              </span>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-y-0.5">
            {Array.from({ length: lead }, (_, i) => (
              <span key={`b${i}`} />
            ))}
            {Array.from({ length: days }, (_, i) => {
              const day = i + 1;
              const value_ = iso(year, month, day);
              const isSelected = value_ === value;

              return (
                <button
                  key={day}
                  type="button"
                  aria-label={new Date(year, month, day).toLocaleDateString(undefined, {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                  })}
                  aria-pressed={isSelected}
                  onClick={() => {
                    onChange(value_);
                    setOpen(false);
                  }}
                  className={cn(
                    "tnum mx-auto flex size-9 items-center justify-center rounded-full text-ui transition-colors duration-150",
                    isSelected
                      ? "bg-board text-chalk"
                      : "text-ink hover:bg-sheet-2",
                    !isSelected && value_ === today && "border border-hl",
                  )}
                >
                  {day}
                </button>
              );
            })}
          </div>

          <div className="mt-2 flex justify-between border-t border-rule pt-2">
            <button
              type="button"
              onClick={() => {
                onChange(today);
                setOpen(false);
              }}
              className="rounded-ctl px-2 py-1 text-ui font-medium text-blue hover:bg-sheet-2"
            >
              Today
            </button>
            <button
              type="button"
              onClick={() => {
                onChange("");
                setOpen(false);
              }}
              className="rounded-ctl px-2 py-1 text-ui text-ink-2 hover:bg-sheet-2"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
