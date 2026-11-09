import type { ReactNode } from "react";
import Logo from "./Logo";
import Wordmark from "./Wordmark";

/**
 * The frame for every screen shown before you are inside the app: sign-in,
 * profile setup, and "could not load your account". The chalkboard panel
 * matches the rail you will see once you are in, and the mark is the hero.
 */
export default function AuthShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="relative h-full overflow-y-auto bg-paper text-ink md:grid md:grid-cols-[5fr_6fr]">
      <aside className="ruled hidden flex-col items-center justify-center bg-board px-12 text-center text-chalk md:flex">
        <Logo size={224} draw className="drop-shadow-[0_12px_24px_rgb(0_0_0/0.25)]" />

        <p className="mt-6 font-serif text-display font-semibold leading-none tracking-tight">
          StudyStream
        </p>

        <p className="mt-5 max-w-[24ch] text-h3 font-serif text-chalk-2">
          Turn your course material into{" "}
          <span className="hl-block">study plans</span>, answers and quizzes.
        </p>
      </aside>

      <main className="flex min-h-screen items-center justify-center px-5 py-10 md:min-h-0 md:px-12">
        <div className="w-full max-w-sm">
          <Wordmark size={34} className="mb-8 text-board md:hidden" />

          <h1 className="text-h1 text-ink">{title}</h1>
          {description && (
            <p className="mt-1.5 mb-6 text-body text-ink-2">{description}</p>
          )}
          {!description && <div className="mb-6" />}

          {children}
        </div>
      </main>
    </div>
  );
}
