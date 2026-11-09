import { cn } from "@/lib/utils";

/**
 * The StudyStream mark: a pencil whose lead leaves a stream behind it.
 *
 * Transparent, and the dark parts follow the surrounding text colour, so the
 * same mark sits on the chalkboard-green rail (light) and on paper (dark). The
 * orange is UTD orange and never changes.
 *
 * public/logo.svg is the same drawing with fixed colours, for places that
 * cannot use React (the README, social previews).
 */
export default function Logo({
  size = 32,
  className,
  draw = false,
}: {
  size?: number;
  className?: string;
  /** Draws the stream in once on mount. For the sign-in hero only. */
  draw?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      role="img"
      aria-label="StudyStream"
      className={cn(draw && "logo-draw", className)}
    >
      <path d="M38.09 1.04 L34.74 6.01 L45.51 13.28 L48.87 8.31 Z" fill="currentColor" stroke="currentColor" strokeWidth="1" strokeLinejoin="round"/>
      <path d="M33.39 8.00 L31.16 11.32 L41.93 18.59 L44.17 15.27 Z" fill="#E87500" stroke="#E87500" strokeWidth="1" strokeLinejoin="round"/>
      <path d="M29.81 13.31 L23.66 22.43 L34.44 29.70 L40.59 20.58 Z" fill="currentColor" stroke="currentColor" strokeWidth="1" strokeLinejoin="round"/>
      <path d="M22.32 24.42 L21.00 38.00 L33.10 31.69 Z" stroke="currentColor" strokeWidth="2.6" strokeLinejoin="round"/>
      <path d="M21.56 32.30 L21.00 38.00 L26.08 35.35 Z" fill="currentColor" stroke="currentColor" strokeWidth="1" strokeLinejoin="round"/>
      <path d="M22.0 44.5 C26.0 54.5 34.0 55.5 40.0 50.5 S53.0 45.5 60.0 53.5" stroke="#E87500" strokeWidth="4.2" strokeLinecap="round" pathLength="1" className="logo-stream"/>
    </svg>
  );
}
