import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  Check,
  Copy,
  GraduationCap,
  Mail,
  Plus,
  UserRoundPlus,
  Users,
} from "lucide-react";
import {
  getRoster,
  getTeacherCode,
  linkTeacher,
  listTeachers,
  unlinkTeacher,
  type RosterPerson,
  type TeacherSummary,
} from "@/lib/api";
import type { WorkspaceContext } from "@/components/Layout";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import { Field, TextInput } from "@/components/ui/form";
import Notice from "@/components/ui/Notice";
import PageHeader from "@/components/ui/PageHeader";
import PageShell from "@/components/ui/PageShell";
import Panel from "@/components/ui/Panel";
import Skeleton from "@/components/ui/Skeleton";
import { Table, Td, Th } from "@/components/ui/Table";
import Tag from "@/components/ui/Tag";

export default function TeachersView() {
  const { role } = useOutletContext<WorkspaceContext>();
  const isTeacher = role === "teacher";

  return (
    <PageShell>
      <PageHeader
        title={isTeacher ? "Your class" : "Teachers"}
        description={
          isTeacher
            ? "Give students and TAs your code to share your subjects with them."
            : "Enter a teacher's code to see the subjects and files they share."
        }
      />

      {isTeacher ? <TeacherCode /> : <LinkedTeachers />}
    </PageShell>
  );
}

/** The teacher's side: their own code, to read out or paste into a message. */
function TeacherCode() {
  const [data, setData] = useState<{ code: string; students: number } | null>(
    null,
  );
  const [error, setError] = useState("");
  const [people, setPeople] = useState<RosterPerson[] | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getRoster()
      .then((res) => {
        if (!cancelled) setPeople(res.people);
      })
      .catch(() => {
        if (!cancelled) setPeople([]);
      });

    getTeacherCode()
      .then((res) => {
        if (!cancelled) setData({ code: res.code, students: res.students });
      })
      .catch((err) => {
        if (!cancelled)
          setError(
            err instanceof Error ? err.message : "Could not load your code.",
          );
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function copy() {
    if (!data) return;

    try {
      await navigator.clipboard.writeText(data.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the code is on screen to copy by hand.
    }
  }

  if (error) return <Notice tone="error">{error}</Notice>;

  return (
    <div className="space-y-4">
      <Panel
        title="Your teacher code"
        icon={GraduationCap}
        subtitle="Students and TAs who enter it see your public subjects under Shared."
      >
        {!data ? (
          <Skeleton className="h-10 w-56" />
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-4">
              <p
                className="tnum rounded-ctl bg-sheet-2 px-5 py-3 font-serif text-h1 tracking-wider text-ink"
                aria-label={`Your code is ${data.code.split("").join(" ")}`}
              >
                {data.code}
              </p>
              <Button icon={copied ? Check : Copy} onClick={copy}>
                {copied ? "Copied" : "Copy code"}
              </Button>
            </div>

            <p className="mt-4 text-body text-ink-2">
              {data.students === 0
                ? "Nobody has entered it yet."
                : `${data.students} ${data.students === 1 ? "person has" : "people have"} entered it.`}{" "}
              Make a subject <strong>Public</strong> when you add it, and
              everyone with your code sees it and the files you upload to it.
            </p>
          </>
        )}
      </Panel>

      <Panel
        title="Linked students and TAs"
        icon={Users}
        subtitle="Names and emails only. Their questions and scores stay private."
        flush
      >
        {people === null ? (
          <div
            role="status"
            aria-label="Loading"
            className="space-y-3 p-5 md:p-6"
          >
            <Skeleton className="h-5 w-3/5" />
            <Skeleton className="h-5 w-2/5" />
          </div>
        ) : people.length === 0 ? (
          <p className="p-5 text-ui text-ink-2 md:p-6">
            Nobody has entered your code yet.
          </p>
        ) : (
          <Table label="Linked students and TAs">
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Role</Th>
                <Th>Email</Th>
              </tr>
            </thead>
            <tbody>
              {people.map((p) => (
                <tr key={p.id}>
                  <Td className="font-medium">{p.full_name}</Td>
                  <Td>
                    <Tag>{p.role === "ta" ? "TA" : "Student"}</Tag>
                  </Td>
                  <Td>
                    {p.email ? (
                      <a
                        href={`mailto:${p.email}`}
                        className="text-blue underline underline-offset-2"
                      >
                        {p.email}
                      </a>
                    ) : (
                      <span className="text-ink-3">Not available</span>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Panel>
    </div>
  );
}

/** The student's (or TA's) side: add a code, see who they follow. */
function LinkedTeachers() {
  const { refreshCourses } = useOutletContext<WorkspaceContext>();

  const [teachers, setTeachers] = useState<TeacherSummary[] | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [added, setAdded] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    listTeachers()
      .then((res) => {
        if (!cancelled) setTeachers(res.teachers);
      })
      .catch((err) => {
        if (cancelled) return;
        setTeachers([]);
        setError(
          err instanceof Error ? err.message : "Could not load your teachers.",
        );
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim() || busy) return;

    setBusy(true);
    setError("");
    setAdded("");

    try {
      const { teacher } = await linkTeacher(code);

      setTeachers((list) => [
        ...(list ?? []).filter((t) => t.id !== teacher.id),
        teacher,
      ]);
      setAdded(`You can now see ${teacher.full_name}'s shared subjects.`);
      setCode("");
      refreshCourses();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That code did not work.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setError("");
    setAdded("");

    try {
      await unlinkTeacher(id);
      setTeachers((list) => (list ?? []).filter((t) => t.id !== id));
      setConfirming(null);
      refreshCourses();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not do that.");
    }
  }

  return (
    <div className="space-y-4">
      <Panel
        title="Add a teacher code"
        icon={UserRoundPlus}
        subtitle="Your teacher gives you this code. It looks like ABCD-2345."
      >
        <form onSubmit={add} className="flex flex-wrap items-end gap-3">
          <div className="w-72 max-w-full">
            <Field label="Teacher code">
              {(id) => (
                <TextInput
                  id={id}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="ABCD-2345"
                  maxLength={12}
                  autoComplete="off"
                  spellCheck={false}
                  className="tnum uppercase tracking-wider"
                />
              )}
            </Field>
          </div>
          <Button
            type="submit"
            variant="primary"
            icon={Plus}
            loading={busy}
            disabled={!code.trim()}
          >
            Add
          </Button>
        </form>

        {error && (
          <Notice tone="error" className="mt-4">
            {error}
          </Notice>
        )}
        {added && (
          <Notice tone="ok" className="mt-4">
            {added}
          </Notice>
        )}
      </Panel>

      {teachers === null ? (
        <Panel title="Your teachers">
          <div role="status" aria-label="Loading" className="space-y-3">
            <Skeleton className="h-5 w-3/5" />
            <Skeleton className="h-5 w-2/5" />
          </div>
        </Panel>
      ) : teachers.length === 0 ? (
        <EmptyState title="No teachers yet">
          Once you add a code, the teacher's name, email and shared subjects
          appear here, and their subjects show up under Shared in the sidebar.
        </EmptyState>
      ) : (
        teachers.map((t) => (
          <Panel
            key={t.id}
            title={t.full_name}
            icon={GraduationCap}
            actions={
              confirming === t.id ? (
                <>
                  <span className="text-ui text-ink-2">
                    Remove their subjects?
                  </span>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => remove(t.id)}
                  >
                    Stop following
                  </Button>
                  <Button size="sm" onClick={() => setConfirming(null)}>
                    Keep
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setConfirming(t.id)}
                >
                  Stop following
                </Button>
              )
            }
          >
            {t.email && (
              <p className="flex items-center gap-2 text-body text-ink">
                <Mail className="size-4 shrink-0 text-ink-2" aria-hidden />
                <a
                  href={`mailto:${t.email}`}
                  className="text-blue underline underline-offset-2"
                >
                  {t.email}
                </a>
              </p>
            )}

            <h3 className="mt-5 mb-2 font-sans text-ui font-medium text-ink-2">
              Shared subjects
            </h3>

            {t.subjects.length === 0 ? (
              <p className="text-ui text-ink-2">
                They have not shared any subjects yet.
              </p>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {t.subjects.map((s) => (
                  <li key={s.id}>
                    <Tag tone="mark" title={s.name}>
                      <strong className="font-semibold">{s.id}</strong>
                      {s.name !== s.id && (
                        <span className="font-normal"> · {s.name}</span>
                      )}
                    </Tag>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        ))
      )}
    </div>
  );
}
