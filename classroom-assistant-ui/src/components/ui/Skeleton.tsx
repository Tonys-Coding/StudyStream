import { cn } from "@/lib/utils";

/** A grey bar standing where text will be, so loading does not shift layout. */
export default function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("h-4 animate-pulse rounded-tag bg-sheet-2", className)}
    />
  );
}
