import type { AskResponse } from "@/lib/api";
import { TAB_META, type TabId } from "./tabs";

interface Props {
  result: AskResponse;
  onJumpToTab: (tab: TabId) => void;
}

/** Highlight chips summarizing what each agent produced. */
function highlights(result: AskResponse): { tab: TabId; label: string }[] {
  const out: { tab: TabId; label: string }[] = [];

  const study = result.agents.study;
  if (study?.success) {
    out.push({
      tab: "study",
      label: `${study.response.study_plan.length} study steps`,
    });
    if (study.response.estimated_hours !== null) {
      out.push({
        tab: "study",
        label: `${study.response.estimated_hours} hours estimated`,
      });
    }
  }

  const quiz = result.agents.quiz;
  if (quiz?.success) {
    out.push({
      tab: "assessment",
      label: `${quiz.response.questions.length} practice questions`,
    });
  }

  const faq = result.agents.faq;
  if (faq?.success) {
    out.push({ tab: "faq", label: "Course answer available" });
  }

  return out;
}

export default function OverviewPanel({ result, onJumpToTab }: Props) {
  const chips = highlights(result);

  const failures = (["study", "quiz", "faq"] as const)
    .map((slug) => ({ slug, entry: result.agents[slug] }))
    .filter((x) => x.entry && !x.entry.success);

  return (
    <>
      <div className="paper-card rounded-xl p-8 mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="material-symbols-outlined filled text-primary text-[28px]">
            auto_awesome
          </span>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">
            Overview
          </h2>
        </div>

        <p className="font-body-notebook text-body-notebook text-on-surface-variant max-w-4xl leading-relaxed mb-6">
          {result.overview}
        </p>

        {chips.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {chips.map((chip) => (
              <button
                key={chip.label}
                onClick={() => onJumpToTab(chip.tab)}
                className="px-3 py-1 bg-scholar-gold-muted text-secondary rounded-full font-label-sm text-label-sm border border-secondary/20 hover:border-secondary/50 transition-colors"
              >
                {chip.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Cards for each tab that has content, so the overview is a hub */}
      <div className="grid gap-4 sm:grid-cols-2">
        {result.selected_agents
          .filter((slug) => result.agents[slug]?.success)
          .map((slug) => {
            const meta = TAB_META[slug === "quiz" ? "assessment" : slug];

            return (
              <button
                key={slug}
                onClick={() => onJumpToTab(meta.id)}
                className="paper-card paper-card-interactive rounded-xl p-5 text-left"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="material-symbols-outlined text-primary">
                    {meta.icon}
                  </span>
                  <h3 className="font-title-md text-title-md text-on-surface">
                    {meta.label}
                  </h3>
                </div>
                <p className="text-label-sm text-on-surface-variant">
                  {meta.blurb}
                </p>
              </button>
            );
          })}
      </div>

      {failures.length > 0 && (
        <div className="mt-8 rounded-xl border border-error/30 bg-error-container/40 p-5">
          <h3 className="font-title-md text-title-md text-on-error-container mb-2">
            Not available for this question
          </h3>
          <ul className="space-y-1">
            {failures.map(({ slug, entry }) => (
              <li key={slug} className="text-label-sm text-on-surface-variant">
                <span className="font-medium capitalize">{slug}</span>:{" "}
                {entry && !entry.success ? entry.message : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
