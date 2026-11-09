import { useRef, useState } from "react";
import { Check, ClipboardCheck, X } from "lucide-react";
import { recordQuiz, type QuizResponse } from "@/lib/api";
import Button from "@/components/ui/Button";
import Notice from "@/components/ui/Notice";
import Panel from "@/components/ui/Panel";
import { cn } from "@/lib/utils";
import SourceList from "./SourceList";

interface Props {
  data: QuizResponse;
  courseId: string;
  /** What the student asked, saved with the result. */
  topic: string;
}

const LETTERS = ["A", "B", "C", "D"];

export default function QuizPanel({ data, courseId, topic }: Props) {
  // Which question index -> which choice the student picked
  const [picked, setPicked] = useState<Record<number, string>>({});
  const pickedRef = useRef<Record<number, string>>({});
  const [revealed, setRevealed] = useState<Set<number>>(new Set());
  const [saveState, setSaveState] = useState<"idle" | "saved" | "failed">(
    "idle",
  );

  function choose(questionIndex: number, choice: string) {
    // Built from the latest picks, so two answers in quick succession both count.
    const next = { ...pickedRef.current, [questionIndex]: choice };

    pickedRef.current = next;
    setPicked(next);
    setRevealed((prev) => new Set(prev).add(questionIndex));

    // The last answer finishes the quiz: save the score so it shows up on
    // the Dashboard. Peeking with "Show answer" does not count as answering.
    if (Object.keys(next).length === data.questions.length) {
      const score = data.questions.filter(
        (q, i) => next[i] === q.answer,
      ).length;

      recordQuiz(courseId, topic, score, data.questions.length)
        .then(() => setSaveState("saved"))
        .catch(() => setSaveState("failed"));
    }
  }

  const answered = Object.keys(picked).length;
  const correct = data.questions.filter(
    (q, i) => picked[i] === q.answer,
  ).length;

  return (
    <Panel
      title="Practice quiz"
      icon={ClipboardCheck}
      subtitle={`${data.questions.length} questions`}
      actions={
        <p className="tnum text-body font-medium text-ink" aria-live="polite">
          {correct} of {data.questions.length} correct
          {answered < data.questions.length && (
            <span className="font-normal text-ink-2">
              {" "}
              · {answered} answered
            </span>
          )}
        </p>
      }
    >
      <ol className="divide-y divide-rule">
        {data.questions.map((q, i) => {
          const showing = revealed.has(i);
          const choice = picked[i];

          return (
            <li key={i} className="py-6 first:pt-0 last:pb-0">
              <div className="mb-4 grid grid-cols-[2.25rem_1fr] gap-3">
                <span className="tnum font-serif text-h2 leading-none text-ink-3">
                  {i + 1}
                </span>
                <p className="prose-read text-ink">{q.question}</p>
              </div>

              <div
                role="group"
                aria-label={`Choices for question ${i + 1}`}
                className="space-y-2 sm:pl-12"
              >
                {q.choices.map((option, n) => {
                  const isAnswer = option === q.answer;
                  const isPicked = option === choice;

                  const state = !showing
                    ? "open"
                    : isAnswer
                      ? "right"
                      : isPicked
                        ? "wrong"
                        : "rest";

                  return (
                    <button
                      key={option}
                      disabled={showing}
                      onClick={() => choose(i, option)}
                      className={cn(
                        "flex w-full items-start gap-3 rounded-ctl border px-3.5 py-2.5 text-left text-body transition-colors duration-150",
                        state === "open" &&
                          "border-line bg-sheet text-ink hover:bg-sheet-2",
                        state === "right" && "border-ok bg-ok-soft text-ink",
                        state === "wrong" && "border-red bg-red-soft text-ink",
                        state === "rest" &&
                          "border-rule bg-sheet text-ink-2 opacity-70",
                      )}
                    >
                      <span
                        aria-hidden
                        className={cn(
                          "mt-px flex size-6 shrink-0 items-center justify-center rounded-tag border text-meta font-semibold",
                          state === "right" && "border-ok bg-ok text-white",
                          state === "wrong" && "border-red bg-red text-white",
                          (state === "open" || state === "rest") &&
                            "border-line text-ink-2",
                        )}
                      >
                        {state === "right" ? (
                          <Check className="size-4" />
                        ) : state === "wrong" ? (
                          <X className="size-4" />
                        ) : (
                          LETTERS[n]
                        )}
                      </span>
                      <span className="min-w-0 flex-1">{option}</span>
                      {state === "right" && (
                        <span className="sr-only">Correct answer</span>
                      )}
                      {state === "wrong" && (
                        <span className="sr-only">Your answer, incorrect</span>
                      )}
                    </button>
                  );
                })}
              </div>

              {showing && (
                <p
                  role="status"
                  className={cn(
                    "mt-3 text-ui font-medium sm:pl-12",
                    choice === undefined || choice !== q.answer
                      ? "text-red"
                      : "text-ok",
                  )}
                >
                  {choice === q.answer
                    ? "Correct. "
                    : choice === undefined
                      ? `The answer is "${q.answer}". `
                      : `Not quite. The answer is "${q.answer}". `}
                  {q.explanation}
                </p>
              )}

              {!showing && (
                <div className="mt-3 sm:pl-12">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setRevealed((prev) => new Set(prev).add(i))}
                  >
                    Show answer
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {saveState === "saved" && (
        <Notice tone="ok" className="mt-6">
          Finished. {correct} of {data.questions.length} correct, saved to your
          Dashboard.
        </Notice>
      )}
      {saveState === "failed" && (
        <Notice tone="error" className="mt-6">
          Could not save this result to your Dashboard.
        </Notice>
      )}

      <SourceList sources={data.sources} label="Written from" />
    </Panel>
  );
}
