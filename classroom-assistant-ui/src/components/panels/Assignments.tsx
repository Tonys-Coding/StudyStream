import { useEffect, useState } from "react";
import { Check, ListTodo, Pencil, Plus, Trash2 } from "lucide-react";
import {
  addAssignment,
  deleteAssignment,
  listAssignments,
  updateAssignment,
  type Assignment,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import Button, { IconButton } from "@/components/ui/Button";
import DatePicker from "@/components/ui/DatePicker";
import { Field, Select, TextInput } from "@/components/ui/form";
import Notice from "@/components/ui/Notice";
import Panel from "@/components/ui/Panel";
import Skeleton from "@/components/ui/Skeleton";
import Tag from "@/components/ui/Tag";

interface Subject {
  id: string;
  name: string;
}

/** Not done first, soonest due first, no date last. */
function sorted(items: Assignment[]): Assignment[] {
  return [...items].sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1;
    if (a.due_date !== b.due_date) {
      if (!a.due_date) return 1;
      if (!b.due_date) return -1;
      return a.due_date < b.due_date ? -1 : 1;
    }
    return a.id - b.id;
  });
}

/** Whole days from today to a YYYY-MM-DD date, in the user's own timezone. */
function daysUntil(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  const due = new Date(y, m - 1, d).getTime();
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();

  return Math.round((due - today) / 86_400_000);
}

function dueLabel(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);

  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function DueTag({ item }: { item: Assignment }) {
  if (!item.due_date) return null;

  const days = daysUntil(item.due_date);
  const label = dueLabel(item.due_date);

  if (item.done) return <Tag>{label}</Tag>;
  if (days < 0) return <Tag tone="danger">Overdue · {label}</Tag>;
  if (days === 0) return <Tag tone="mark">Due today</Tag>;
  if (days === 1) return <Tag tone="mark">Due tomorrow</Tag>;

  return <Tag>{label}</Tag>;
}

interface FormProps {
  subjects: Subject[];
  initial?: Assignment;
  submitLabel: string;
  busy: boolean;
  onSubmit: (v: {
    title: string;
    course_id: string | null;
    due_date: string | null;
  }) => void;
  onCancel?: () => void;
}

/** One form for adding and for editing, so they cannot drift apart. */
function AssignmentForm({ subjects, initial, submitLabel, busy, onSubmit, onCancel }: FormProps) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [course, setCourse] = useState(initial?.course_id ?? "");
  const [due, setDue] = useState(initial?.due_date ?? "");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();

        if (!title.trim()) return;

        onSubmit({
          title: title.trim(),
          course_id: course || null,
          due_date: due || null,
        });

        if (!initial) {
          setTitle("");
          setDue("");
        }
      }}
      className="grid gap-3 md:grid-cols-[1fr_11rem_11rem_auto] md:items-end"
    >
      <Field label="Assignment">
        {(id) => (
          <TextInput
            id={id}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Essay draft, problem set 4…"
            maxLength={200}
            required
          />
        )}
      </Field>

      <Field label="Subject">
        {(id) => (
          <Select id={id} value={course} onChange={(e) => setCourse(e.target.value)}>
            <option value="">None</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <Field label="Due">
        {(id) => (
          <DatePicker id={id} value={due} onChange={setDue} />
        )}
      </Field>

      <div className="flex gap-2">
        <Button
          type="submit"
          variant="primary"
          icon={initial ? Check : Plus}
          loading={busy}
          disabled={!title.trim()}
        >
          {submitLabel}
        </Button>
        {onCancel && <Button onClick={onCancel}>Cancel</Button>}
      </div>
    </form>
  );
}

export default function Assignments({ subjects }: { subjects: Subject[] }) {
  const [items, setItems] = useState<Assignment[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    listAssignments()
      .then((res) => {
        if (!cancelled) setItems(sorted(res.assignments));
      })
      .catch((err) => {
        if (cancelled) return;
        setItems([]);
        setError(err instanceof Error ? err.message : "Could not load assignments.");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  /** Runs one change, reporting a failure instead of dropping it. */
  async function run(action: () => Promise<void>) {
    setError("");
    setBusy(true);

    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That did not save.");
    } finally {
      setBusy(false);
    }
  }

  const replace = (a: Assignment) =>
    setItems((list) => sorted((list ?? []).map((x) => (x.id === a.id ? a : x))));

  const open = (items ?? []).filter((a) => !a.done).length;

  return (
    <Panel
      title="Upcoming assignments"
      subtitle="Your own list. Private to you"
      icon={ListTodo}
    >
      <AssignmentForm
        subjects={subjects}
        submitLabel="Add"
        busy={busy && editing === null}
        onSubmit={(v) =>
          run(async () => {
            const { assignment } = await addAssignment(v);
            setItems((list) => sorted([...(list ?? []), assignment]));
          })
        }
      />

      {error && (
        <Notice tone="error" className="mt-4">
          {error}
        </Notice>
      )}

      <div className="mt-5">
        {items === null ? (
          <div role="status" aria-label="Loading" className="space-y-3">
            <Skeleton className="h-5 w-4/5" />
            <Skeleton className="h-5 w-3/5" />
          </div>
        ) : items.length === 0 ? (
          error ? null : (
          <p className="text-ui text-ink-2">
            Nothing due. Add what you have coming up and it will show here,
            soonest first.
          </p>
          )
        ) : (
          <>
            <p className="mb-2 text-meta text-ink-2">
              {open === 0 ? "All done." : `${open} to do`}
            </p>

            <ul className="divide-y divide-rule border-y border-rule">
              {items.map((a) =>
                editing === a.id ? (
                  <li key={a.id} className="py-4">
                    <AssignmentForm
                      subjects={subjects}
                      initial={a}
                      submitLabel="Save"
                      busy={busy}
                      onCancel={() => setEditing(null)}
                      onSubmit={(v) =>
                        run(async () => {
                          const { assignment } = await updateAssignment(a.id, v);
                          replace(assignment);
                          setEditing(null);
                        })
                      }
                    />
                  </li>
                ) : (
                  <li key={a.id} className="flex items-center gap-3 py-3">
                    <button
                      type="button"
                      role="checkbox"
                      aria-checked={a.done}
                      aria-label={`${a.done ? "Mark not done" : "Mark done"}: ${a.title}`}
                      onClick={() =>
                        run(async () => {
                          const { assignment } = await updateAssignment(a.id, {
                            done: !a.done,
                          });
                          replace(assignment);
                        })
                      }
                      className={cn(
                        "flex size-6 shrink-0 items-center justify-center rounded-full border transition-colors duration-150",
                        a.done
                          ? "border-board bg-board text-chalk"
                          : "border-line bg-sheet hover:border-ink hover:bg-sheet-2",
                      )}
                    >
                      {a.done && <Check className="size-3.5" aria-hidden />}
                    </button>

                    <div className="min-w-0 flex-1">
                      <p
                        className={cn(
                          "truncate text-body",
                          a.done ? "text-ink-3 line-through" : "text-ink",
                        )}
                      >
                        {a.title}
                      </p>
                    </div>

                    <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
                      {a.course_id && <Tag>{a.course_id}</Tag>}
                      <DueTag item={a} />
                    </div>

                    <IconButton
                      icon={Pencil}
                      label={`Edit ${a.title}`}
                      onClick={() => setEditing(a.id)}
                    />
                    <IconButton
                      icon={Trash2}
                      label={`Delete ${a.title}`}
                      onClick={() =>
                        run(async () => {
                          await deleteAssignment(a.id);
                          setItems((list) => (list ?? []).filter((x) => x.id !== a.id));
                        })
                      }
                    />
                  </li>
                ),
              )}
            </ul>
          </>
        )}
      </div>
    </Panel>
  );
}
