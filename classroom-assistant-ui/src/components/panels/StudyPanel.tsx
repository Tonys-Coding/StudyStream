import type { StudyPlanResponse } from "@/lib/api";

export default function StudyPanel({ data }: { data: StudyPlanResponse }) {
  const focusTopics = data.focus_topics ?? [];

  return (
    <>
      <div className="paper-card rounded-xl p-8 mb-8">
        <div className="flex items-center gap-3 mb-6">
          <span className="material-symbols-outlined filled text-primary text-[28px]">
            calendar_month
          </span>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">
            Study Plan
          </h2>
        </div>

        <div className="flex gap-4 mb-8 flex-wrap">
          <div className="bg-academy-blue-light rounded-xl px-5 py-3 min-w-40">
            <p className="text-label-sm text-on-surface-variant uppercase">
              Steps
            </p>
            <p className="font-headline-lg text-headline-lg text-primary">
              {data.study_plan.length}
            </p>
          </div>
          <div className="bg-academy-blue-light rounded-xl px-5 py-3 min-w-40">
            <p className="text-label-sm text-on-surface-variant uppercase">
              Focus topics
            </p>
            <p className="font-headline-lg text-headline-lg text-primary">
              {focusTopics.length}
            </p>
          </div>
          <div className="bg-scholar-gold-muted rounded-xl px-5 py-3 min-w-40">
            <p className="text-label-sm text-on-surface-variant uppercase">
              Estimated time
            </p>
            <p className="font-headline-lg text-headline-lg text-secondary">
              {data.estimated_hours === null ? "—" : `${data.estimated_hours}h`}
            </p>
          </div>
        </div>

        <ol className="space-y-3">
          {data.study_plan.map((step, i) => (
            <li
              key={i}
              className="flex gap-4 border border-chalkboard-border rounded-xl p-4"
            >
              <span className="bg-primary text-on-primary text-label-sm font-medium rounded-full w-7 h-7 flex items-center justify-center shrink-0">
                {i + 1}
              </span>
              <p className="font-body-notebook text-body-notebook text-on-surface-variant leading-relaxed">
                {step}
              </p>
            </li>
          ))}
        </ol>
      </div>

      {focusTopics.length > 0 && (
        <div className="paper-card rounded-xl p-8">
          <h3 className="font-title-md text-title-md text-on-surface mb-4">
            Focus topics
          </h3>
          <div className="flex gap-2 flex-wrap">
            {focusTopics.map((topic) => (
              <span
                key={topic}
                className="px-3 py-1 bg-scholar-gold-muted text-secondary rounded-full font-label-sm text-label-sm border border-secondary/20"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
