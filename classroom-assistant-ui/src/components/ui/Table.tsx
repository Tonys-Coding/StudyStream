import type { ReactNode, ThHTMLAttributes, TdHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** One table style for the whole app: hairline rules, no zebra, no boxes. */
export function Table({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="overflow-x-auto">
      <table aria-label={label} className="w-full border-collapse text-ui">
        {children}
      </table>
    </div>
  );
}

interface CellProps {
  align?: "left" | "right";
}

export function Th({
  align = "left",
  className,
  ...rest
}: ThHTMLAttributes<HTMLTableCellElement> & CellProps) {
  return (
    <th
      scope="col"
      className={cn(
        "whitespace-nowrap border-b border-rule bg-sheet-2/60 px-5 py-2.5 text-meta font-medium text-ink-2 first:pl-5 md:first:pl-6",
        align === "right" ? "text-right" : "text-left",
        className,
      )}
      {...rest}
    />
  );
}

export function Td({
  align = "left",
  className,
  ...rest
}: TdHTMLAttributes<HTMLTableCellElement> & CellProps) {
  return (
    <td
      className={cn(
        "border-b border-rule/70 px-5 py-3 align-top text-ink first:pl-5 md:first:pl-6",
        align === "right" && "text-right",
        className,
      )}
      {...rest}
    />
  );
}
