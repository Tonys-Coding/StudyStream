import { cn } from "@/lib/utils";
import Logo from "./Logo";

/** The mark and the name together. Inherits its colour from the surface. */
export default function Wordmark({
  size = 34,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Logo size={size} />
      <span className="font-serif text-[1.375rem] font-semibold leading-none tracking-tight">
        StudyStream
      </span>
    </span>
  );
}
