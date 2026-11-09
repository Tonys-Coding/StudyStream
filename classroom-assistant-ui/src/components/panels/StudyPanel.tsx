import { ListChecks } from "lucide-react";
import type { StudyPlanResponse } from "@/lib/api";
import Panel from "@/components/ui/Panel";
import SourceList from "./SourceList";

function hours(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

export default function StudyPanel({ data }: { data: StudyPlanResponse }) {
  const focusTopics = data.focus_topics ?? [];

  const subtitle =
    `${data.study_plan.length} steps` +
    (data.estimated_hours !== null
      ? ` · about ${hours(data.estimated_hours)} hours`
      : "");

  return (
    <Panel title="Study plan" subtitle={subtitle} icon={ListChecks}>
      <ol className="divide-y divide-rule">
        {data.study_plan.map((step, i) => (
          <li
            key={i}
            className="grid grid-cols-[2.25rem_1fr] gap-3 py-4 first:pt-0 last:pb-0"
          >
            <span className="tnum font-serif text-h2 leading-none text-ink-3">
              {i + 1}
            </span>
            <p className="prose-read text-ink">{step}</p>
          </li>
        ))}
      </ol>

      {focusTopics.length > 0 && (
        <div className="mt-6 border-t border-rule pt-5">
          <h3 className="mb-3 text-h3 text-ink">Focus topics</h3>
          {/* The marker is for what matters most: these are the topics to
              spend your time on. */}
          <ul className="flex flex-wrap gap-x-5 gap-y-3 pl-1">
            {focusTopics.map((topic) => (
              <li key={topic} className="text-body font-medium text-ink">
                <span className="hl">{topic}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <SourceList sources={data.sources} label="Built from" />
    </Panel>
  );
}
