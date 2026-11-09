import { Loader2, type LucideIcon } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "sm";

const VARIANT: Record<Variant, string> = {
  // The one filled action on a screen. Chalkboard green, like the rail.
  primary:
    "bg-board text-chalk shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_1px_2px_rgb(29_36_32/0.3)] hover:bg-board-2",
  secondary: "bg-sheet text-ink border border-line hover:bg-sheet-2",
  ghost: "text-ink-2 hover:bg-sheet-2 hover:text-ink",
  // Red pen. Only for things that cannot be undone.
  danger: "bg-red text-white hover:bg-[#8f2118]",
};

const SIZE: Record<Size, string> = {
  md: "h-10 px-4 text-ui gap-2",
  sm: "h-8 px-3 text-meta gap-1.5",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: LucideIcon;
  /** Shows a spinner in place of the icon and blocks clicks. */
  loading?: boolean;
}

export default function Button({
  variant = "secondary",
  size = "md",
  icon: Icon,
  loading = false,
  className,
  children,
  disabled,
  type = "button",
  ...rest
}: Props) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-ctl font-medium whitespace-nowrap",
        "transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50",
        SIZE[size],
        VARIANT[variant],
        className,
      )}
      {...rest}
    >
      {loading ? (
        <Loader2 className="size-4 animate-spin" aria-hidden />
      ) : (
        Icon && <Icon className="size-4" aria-hidden />
      )}
      {children}
    </button>
  );
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  /** Required: an icon alone says nothing to a screen reader. */
  label: string;
  /** For buttons that sit on the dark rail. */
  onDark?: boolean;
}

export function IconButton({
  icon: Icon,
  label,
  onDark = false,
  className,
  type = "button",
  ...rest
}: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex size-9 shrink-0 items-center justify-center rounded-ctl transition-colors duration-150",
        "disabled:cursor-not-allowed disabled:opacity-40",
        onDark
          ? "text-chalk-2 hover:bg-board-2 hover:text-chalk"
          : "text-ink-2 hover:bg-sheet-2 hover:text-ink",
        className,
      )}
      {...rest}
    >
      <Icon className="size-[18px]" aria-hidden />
    </button>
  );
}
