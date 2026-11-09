import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PanelProps {
  title?: string;
  /** One line under the title: counts, scope, who can see this. */
  subtitle?: string;
  icon?: LucideIcon;
  /** Buttons that act on the whole panel. */
  actions?: ReactNode;
  /** Drops the body padding, for a table that runs edge to edge. */
  flush?: boolean;
  className?: string;
  children: ReactNode;
}

/**
 * The container for every block of content. A flat sheet with a hairline
 * border: no shadow, no texture, and never a panel inside a panel.
 */
export default function Panel({
  title,
  subtitle,
  icon: Icon,
  actions,
  flush = false,
  className,
  children,
}: PanelProps) {
  return (
    <section
      className={cn(
        "rounded-panel border border-rule bg-sheet shadow-[0_1px_2px_rgb(29_36_32/0.05),0_8px_20px_-14px_rgb(29_36_32/0.28)]",
        className,
      )}
    >
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-rule px-5 py-4 md:px-6">
          <div className="min-w-0">
            {title && (
              <h2 className="flex items-center gap-2 text-h3 text-ink">
                {Icon && <Icon className="size-5 shrink-0 text-ink-2" aria-hidden />}
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-0.5 text-ui text-ink-2">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}

      <div className={flush ? "" : "p-5 md:p-6"}>{children}</div>
    </section>
  );
}
