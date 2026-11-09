import { AlertCircle, CheckCircle2, Info, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Tone = "error" | "ok" | "info";

const TONE: Record<Tone, { box: string; icon: string; Icon: LucideIcon }> = {
  error: { box: "border-red/40 bg-red-soft", icon: "text-red", Icon: AlertCircle },
  ok: { box: "border-ok/40 bg-ok-soft", icon: "text-ok", Icon: CheckCircle2 },
  info: { box: "border-rule bg-sheet-2", icon: "text-ink-2", Icon: Info },
};

/**
 * An inline message. Errors say what went wrong and what to do; they sit
 * where the problem is rather than in a modal.
 */
export default function Notice({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: Tone;
  title?: string;
  children?: ReactNode;
  className?: string;
}) {
  const { box, icon, Icon } = TONE[tone];

  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-ctl border p-3.5 text-ui text-ink", box, className)}
    >
      <Icon className={cn("mt-0.5 size-[18px] shrink-0", icon)} aria-hidden />
      <div className="min-w-0">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={title ? "mt-0.5 text-ink-2" : ""}>{children}</div>}
      </div>
    </div>
  );
}
