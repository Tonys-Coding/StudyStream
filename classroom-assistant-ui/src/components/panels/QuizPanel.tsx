import { useState } from "react";
import type { QuizResponse } from "@/lib/api";

export default function QuizPanel({ data }: { data: QuizResponse }) {
  // Which question index -> which choice the student picked
  const [picked, setPicked] = useState<Record<number, string>>({});
  const [revealed, setRevealed] = useState<Set<number>>(new Set());

  function choose(questionIndex: number, choice: string) {
    setPicked((prev) => ({ ...prev, [questionIndex]: choice }));
    setRevealed((prev) => new Set(prev).add(questionIndex));
  }

  const answered = Object.keys(picked).length;
  const correct = data.questions.filter(
    (q, i) => picked[i] === q.answer,
  ).length;

  return (
    <>
      <div className="paper-card rounded-xl p-8 mb-8">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined filled text-primary text-[28px]">
              assignment
            </span>
            <h2 className="font-headline-lg text-headline-lg text-on-surface">
              Practice Questions
            </h2>
          </div>

          <div className="bg-academy-blue-light rounded-xl px-5 py-2">
            <p className="text-label-sm text-on-surface-variant uppercase">
              Score
            </p>
            <p className="font-title-md text-title-md text-primary">
              {correct} / {data.questions.length}
              {answered < data.questions.length && (
                <span className="text-on-surface-variant">
                  {" "}
                  ({answered} answered)
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {data.questions.map((q, i) => {
          const showing = revealed.has(i);
          const choice = picked[i];

          return (
            <div key={i} className="paper-card rounded-xl p-6">
              <div className="flex gap-4 mb-4">
                <span className="bg-primary text-on-primary text-label-sm font-medium rounded-full w-7 h-7 flex items-center justify-center shrink-0">
                  {i + 1}
                </span>
                <p className="font-body-notebook text-body-notebook text-on-surface leading-relaxed">
                  {q.question}
                </p>
              </div>

              <div className="space-y-2 ml-11">
                {q.choices.map((option) => {
                  const isAnswer = option === q.answer;
                  const isPicked = option === choice;

                  let tone =
                    "border-chalkboard-border hover:border-primary hover:bg-surface-container-low";

                  if (showing && isAnswer) {
                    tone = "border-primary bg-academy-blue-light text-primary";
                  } else if (showing && isPicked && !isAnswer) {
                    tone =
                      "border-error bg-error-container/50 text-on-error-container";
                  } else if (showing) {
                    tone = "border-chalkboard-border opacity-60";
                  }

                  return (
                    <button
                      key={option}
                      disabled={showing}
                      onClick={() => choose(i, option)}
                      className={`w-full text-left text-body-md rounded-xl px-4 py-2.5 border transition-colors flex items-center gap-3 ${tone}`}
                    >
                      {showing && isAnswer && (
                        <span className="material-symbols-outlined text-[20px]">
                          check_circle
                        </span>
                      )}
                      {showing && isPicked && !isAnswer && (
                        <span className="material-symbols-outlined text-[20px]">
                          cancel
                        </span>
                      )}
                      <span>{option}</span>
                    </button>
                  );
                })}
              </div>

              {!showing && (
                <button
                  onClick={() =>
                    setRevealed((prev) => new Set(prev).add(i))
                  }
                  className="ml-11 mt-3 text-label-sm text-primary font-medium"
                >
                  Show answer
                </button>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
