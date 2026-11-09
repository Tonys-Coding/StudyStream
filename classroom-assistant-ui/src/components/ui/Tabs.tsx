import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TabItem<Id extends string> {
  id: Id;
  label: string;
  icon: LucideIcon;
  /** Explains why a disabled tab is disabled. */
  disabledReason?: string;
  disabled?: boolean;
  /** A dot for results you have not opened yet. */
  unseen?: boolean;
}

/**
 * Standard tabs. The selected one is highlighted with the marker, drawn in
 * when you switch to it.
 */
export default function Tabs<Id extends string>({
  items,
  value,
  onChange,
  label,
}: {
  items: TabItem<Id>[];
  value: Id;
  onChange: (id: Id) => void;
  label: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className="flex gap-1 overflow-x-auto border-b border-rule"
    >
      {items.map(({ id, label: text, icon: Icon, disabled, disabledReason, unseen }) => {
        const selected = id === value;

        return (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={selected}
            disabled={disabled}
            title={disabled ? disabledReason : undefined}
            onClick={() => onChange(id)}
            className={cn(
              "relative flex h-11 shrink-0 items-center gap-2 px-3.5 text-ui font-medium transition-colors duration-150 md:px-4",
              selected ? "text-ink" : "text-ink-2 hover:text-ink",
              disabled && "cursor-not-allowed text-ink-3/70 hover:text-ink-3/70",
            )}
          >
            <Icon className="size-[18px]" aria-hidden />
            {text}
            {unseen && !selected && (
              <span className="size-1.5 rounded-full bg-board" aria-label="new" />
            )}
            {selected && (
              <span
                aria-hidden
                className="swipe absolute inset-x-2 -bottom-px h-1 rounded-full bg-hl"
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
