import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardCheck, GraduationCap, MessageSquareText, Users } from "lucide-react";
import { getDashboard, type DashboardResponse } from "@/lib/api";
import Assignments from "@/components/panels/Assignments";
import EmptyState from "@/components/ui/EmptyState";
import Notice from "@/components/ui/Notice";
import PageHeader from "@/components/ui/PageHeader";
import PageShell from "@/components/ui/PageShell";
import Panel from "@/components/ui/Panel";
import Skeleton from "@/components/ui/Skeleton";
import { Table, Td, Th } from "@/components/ui/Table";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DashboardResponse };

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** A score as a number and a plain bar, so a column of them can be compared. */
function Score({ value }: { value: number | null }) {
  if (value === null) return <span className="text-ink-3">No quizzes yet</span>;

  return (
    <span className="inline-flex items-center justify-end gap-2.5">
      <span className="tnum font-medium">{value}%</span>
      <span
        aria-hidden
        className="h-2 w-20 overflow-hidden rounded-full bg-sheet-2"
      >
        <span
          className="block h-full rounded-full bg-board"
          style={{ width: `${value}%` }}
        />
      </span>
    </span>
  );
}

export default function DashboardView() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    getDashboard()
      .then((data) => {
        if (!cancelled) setState({ status: "ready", data });
      })
      .catch((err) => {
        if (cancelled) return;
        setState({
          status: "error",
          message:
            err instanceof Error ? err.message : "Could not load the dashboard.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <PageShell>
      <PageHeader
        title="Dashboard"
        description="What you have asked, practised and scored."
      />

      {state.status === "loading" && (
        <Panel title="Your progress">
          <div role="status" aria-label="Loading" className="space-y-3">
            <Skeleton className="h-5 w-11/12" />
            <Skeleton className="h-5 w-2/3" />
          </div>
        </Panel>
      )}

      {state.status === "error" && (
        <Notice tone="error" title="That didn't work">
          {state.message}
        </Notice>
      )}

      {state.status === "ready" && <Ready data={state.data} />}
    </PageShell>
  );
}

function Ready({ data }: { data: DashboardResponse }) {
  const { totals } = data;
  const empty = totals.questions === 0 && totals.quizzes === 0;

  return (
    <div className="space-y-4">
      <Panel title="Your progress" icon={GraduationCap}>
        {empty ? (
          <EmptyState
            title="Nothing to show yet"
            action={
              <Link
                to="/"
                className="font-medium text-blue underline underline-offset-2"
              >
                Go to the workspace
              </Link>
            }
          >
            Ask a question about one of your subjects and finish a practice
            quiz. Your progress appears here.
          </EmptyState>
        ) : (
          // The numbers are in the sentence, where they can be read, instead
          // of in a row of tiles. The marker goes on the one that matters.
          <p className="prose-read text-ink">
            You have asked{" "}
            <strong className="tnum font-semibold">{totals.questions}</strong>{" "}
            {totals.questions === 1 ? "question" : "questions"} and finished{" "}
            <strong className="tnum font-semibold">{totals.quizzes}</strong>{" "}
            {totals.quizzes === 1 ? "quiz" : "quizzes"} across{" "}
            <strong className="tnum font-semibold">{data.courses.length}</strong>{" "}
            {data.courses.length === 1 ? "subject" : "subjects"}
            {totals.avg_score_pct !== null && (
              <>
                , averaging{" "}
                <span className="hl tnum font-semibold">
                  {totals.avg_score_pct}%
                </span>
              </>
            )}
            .
          </p>
        )}
      </Panel>

      {data.courses.length > 0 && (
        <Panel title="By subject" icon={MessageSquareText} flush>
          <Table label="Progress by subject">
            <thead>
              <tr>
                <Th>Subject</Th>
                <Th align="right">Files</Th>
                <Th align="right">Questions</Th>
                <Th align="right">Quizzes</Th>
                <Th align="right">Average score</Th>
              </tr>
            </thead>
            <tbody>
              {data.courses.map((c) => (
                <tr key={c.id}>
                  <Td>
                    <span className="font-medium">{c.id}</span>
                    {c.name !== c.id && (
                      <span className="text-ink-2"> · {c.name}</span>
                    )}
                  </Td>
                  <Td align="right" className="tnum text-ink-2">
                    {c.materials}
                  </Td>
                  <Td align="right" className="tnum text-ink-2">
                    {c.questions}
                  </Td>
                  <Td align="right" className="tnum text-ink-2">
                    {c.quizzes}
                  </Td>
                  <Td align="right">
                    <Score value={c.avg_score_pct} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Panel>
      )}

      {data.recent.length > 0 && (
        <Panel title="Recent activity" icon={ClipboardCheck}>
          <ul className="divide-y divide-rule">
            {data.recent.map((r, i) => (
              <li
                key={i}
                className="flex items-start gap-3 py-3 first:pt-0 last:pb-0"
              >
                {r.kind === "quiz" ? (
                  <ClipboardCheck
                    className="mt-0.5 size-5 shrink-0 text-ink-2"
                    aria-hidden
                  />
                ) : (
                  <MessageSquareText
                    className="mt-0.5 size-5 shrink-0 text-ink-2"
                    aria-hidden
                  />
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-body text-ink">
                    {r.kind === "quiz"
                      ? `Quiz: ${r.score} of ${r.total} correct`
                      : r.message}
                  </p>
                  <p className="truncate text-ui text-ink-2">
                    {r.course_id}
                    {r.kind === "quiz" && r.message ? ` · ${r.message}` : ""}
                  </p>
                </div>
                <span className="shrink-0 text-meta text-ink-3">
                  {when(r.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {data.class_stats && data.class_stats.length > 0 && (
        <Panel
          title="Your classes"
          icon={Users}
          subtitle="Totals across everyone in each subject. Individual students' questions and scores are not shown."
          flush
        >
          <Table label="Class totals">
            <thead>
              <tr>
                <Th>Subject</Th>
                <Th align="right">Enrolled</Th>
                <Th align="right">Active</Th>
                <Th align="right">Questions</Th>
                <Th align="right">Quizzes</Th>
                <Th align="right">Average score</Th>
              </tr>
            </thead>
            <tbody>
              {data.class_stats.map((c) => (
                <tr key={c.id}>
                  <Td className="font-medium">{c.id}</Td>
                  <Td align="right" className="tnum text-ink-2">
                    {c.enrolled}
                  </Td>
                  <Td align="right" className="tnum text-ink-2">
                    {c.active}
                  </Td>
                  <Td align="right" className="tnum text-ink-2">
                    {c.questions}
                  </Td>
                  <Td align="right" className="tnum text-ink-2">
                    {c.quizzes}
                  </Td>
                  <Td align="right">
                    <Score value={c.avg_score_pct} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Panel>
      )}

      <Assignments
        subjects={data.courses.map((c) => ({ id: c.id, name: c.name }))}
      />
    </div>
  );
}
