import type { ReactNode } from "react";

/** Says what is missing and what to do about it, never just "nothing here". */
export default function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-ctl border border-dashed border-line bg-sheet-2/50 px-5 py-6">
      <h3 className="text-h3 text-ink">{title}</h3>
      <p className="mt-1 max-w-[60ch] text-body text-ink-2">{children}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
