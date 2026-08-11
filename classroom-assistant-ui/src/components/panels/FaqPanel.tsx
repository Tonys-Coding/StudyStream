import type { FaqResponse } from "@/lib/api";

interface Props {
  data: FaqResponse;
  question: string;
}

export default function FaqPanel({ data, question }: Props) {
  return (
    <div className="paper-card rounded-xl p-8">
      <div className="flex items-center gap-3 mb-6">
        <span className="material-symbols-outlined filled text-primary text-[28px]">
          quiz
        </span>
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Course Answer
        </h2>
      </div>

      <p className="text-label-sm text-on-surface-variant uppercase mb-2">
        You asked
      </p>
      <p className="font-title-md text-title-md text-on-surface mb-6 pl-4 border-l-2 border-primary">
        {question}
      </p>

      <p className="text-label-sm text-on-surface-variant uppercase mb-2">
        Answer
      </p>
      <p className="font-body-notebook text-body-notebook text-on-surface-variant leading-relaxed whitespace-pre-wrap">
        {data.answer}
      </p>

      <p className="text-label-sm text-outline mt-8 pt-4 border-t border-chalkboard-border">
        Answered from your course material. If something looks wrong, check
        with your instructor.
      </p>
    </div>
  );
}
