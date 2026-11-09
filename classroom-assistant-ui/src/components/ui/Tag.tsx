import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "mark" | "ok" | "danger";

const TONE: Record<Tone, string> = {
  neutral: "bg-sheet-2 text-ink-2 border-rule",
  // Highlighted: shared with the class, or otherwise worth noticing.
  mark: "bg-hl-soft text-ink border-hl",
  ok: "bg-ok-soft text-ok border-ok/30",
  danger: "bg-red-soft text-red border-red/30",
};

/** A short label: a file type, who can see a file, a count. */
export default function Tag({
  tone = "neutral",
  children,
  title,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  title?: string;
  className?: string;
}) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex max-w-full items-center gap-1 rounded-tag border px-2 py-0.5 text-meta font-medium",
        TONE[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
