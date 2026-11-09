import type { ReactNode } from "react";

/** The same width and gutters on every page, so they line up when you switch. */
export default function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-10 md:py-10">
      {children}
    </div>
  );
}
