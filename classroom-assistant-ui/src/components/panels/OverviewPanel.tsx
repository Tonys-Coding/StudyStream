import { ChevronRight } from "lucide-react";
import type { AskResponse } from "@/lib/api";
import Notice from "@/components/ui/Notice";
import Panel from "@/components/ui/Panel";
import { TAB_META, type TabId } from "./tabs";

interface Props {
  result: AskResponse;
  onJumpToTab: (tab: TabId) => void;
}

function hours(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

/** One line per finished result, saying what is in it. */
function ready(result: AskResponse): { tab: TabId; detail: string }[] {
  const out: { tab: TabId; detail: string }[] = [];

  const study = result.agents.study;
  if (study?.success) {
    const { study_plan, estimated_hours } = study.response;
    out.push({
      tab: "study",
      detail:
        `${study_plan.length} steps` +
        (estimated_hours !== null ? `, about ${hours(estimated_hours)} hours` : ""),
    });
  }

  const faq = result.agents.faq;
  if (faq?.success) {
    out.push({ tab: "faq", detail: "A direct answer from your course material" });
  }

  const quiz = result.agents.quiz;
  if (quiz?.success) {
    out.push({
      tab: "assessment",
      detail: `${quiz.response.questions.length} multiple-choice questions`,
    });
  }

  return out;
}

export default function OverviewPanel({ result, onJumpToTab }: Props) {
  const items = ready(result);

  const failures = (["study", "quiz", "faq"] as const)
    .map((slug) => ({ slug, entry: result.agents[slug] }))
    .filter((x) => x.entry && !x.entry.success);

  return (
    <div className="space-y-4">
      <Panel title="Overview" subtitle={`You asked: ${result.query}`}>
        <p className="prose-read text-ink">{result.overview}</p>

        {items.length > 0 && (
          <ul className="mt-6 divide-y divide-rule border-y border-rule">
            {items.map(({ tab, detail }) => {
              const meta = TAB_META[tab];

              return (
                <li key={tab}>
                  <button
                    onClick={() => onJumpToTab(tab)}
                    className="group flex w-full items-center gap-3 py-3 text-left transition-colors duration-150 hover:bg-sheet-2/60"
                  >
                    <meta.icon className="ml-1 size-5 shrink-0 text-ink-2" aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className="block text-body font-medium text-ink">
                        {meta.label}
                      </span>
                      <span className="block text-ui text-ink-2">{detail}</span>
                    </span>
                    <ChevronRight
                      className="mr-1 size-5 shrink-0 text-ink-3 transition-transform duration-150 group-hover:translate-x-0.5"
                      aria-hidden
                    />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>

      {failures.length > 0 && (
        <Notice tone="error" title="Not available for this question">
          <ul className="space-y-1">
            {failures.map(({ slug, entry }) => (
              <li key={slug}>
                <span className="font-medium text-ink">
                  {TAB_META[slug === "quiz" ? "assessment" : slug].label}:
                </span>{" "}
                {entry && !entry.success ? entry.message : ""}
              </li>
            ))}
          </ul>
        </Notice>
      )}
    </div>
  );
}
