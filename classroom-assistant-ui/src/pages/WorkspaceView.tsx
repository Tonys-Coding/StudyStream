import { useCallback, useEffect, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { History, Loader2, Paperclip, Plus, Send, SquarePen, Trash2 } from "lucide-react";
import {
  ask,
  deleteSession,
  getSession,
  isSupportedFile,
  listSessions,
  uploadMaterial,
  SUPPORTED_EXTENSIONS,
  UPLOAD_ACCEPT,
  type AskResponse,
  type SessionSummary,
} from "@/lib/api";
import type { WorkspaceContext } from "@/components/Layout";
import { TAB_META, TAB_ORDER, type TabId } from "@/components/panels/tabs";
import OverviewPanel from "@/components/panels/OverviewPanel";
import StudyPanel from "@/components/panels/StudyPanel";
import QuizPanel from "@/components/panels/QuizPanel";
import FaqPanel from "@/components/panels/FaqPanel";
import MaterialsTable from "@/components/panels/MaterialsTable";
import Button, { IconButton } from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import { TextInput } from "@/components/ui/form";
import Notice from "@/components/ui/Notice";
import PageHeader from "@/components/ui/PageHeader";
import PageShell from "@/components/ui/PageShell";
import Panel from "@/components/ui/Panel";
import Skeleton from "@/components/ui/Skeleton";
import Tabs, { type TabItem } from "@/components/ui/Tabs";
import Tag from "@/components/ui/Tag";

const SUGGESTIONS = [
  "Help me get ready for the midterm",
  "What is the grading breakdown?",
  "Quiz me on the main concepts",
];

function sessionDate(iso: string): string {
  const d = new Date(iso);

  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
}

/**
 * Keyed by subject, so choosing another subject mounts a fresh workspace: no
 * leftover answer, the Overview tab, and that subject's own chat history.
 */
export default function WorkspaceView() {
  const ctx = useOutletContext<WorkspaceContext>();

  return <Workspace key={ctx.courseId} {...ctx} />;
}

function Workspace({
  courseId,
  courseName,
  materials,
  materialsLoading,
  refreshMaterials,
  role,
  promptAddCourse,
}: WorkspaceContext) {
  const [input, setInput] = useState("");
  const [tab, setTab] = useState<TabId>("overview");
  const [opened, setOpened] = useState<Set<TabId>>(new Set());
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [added, setAdded] = useState("");
  const [uploading, setUploading] = useState(false);

  // Chat history. null means "still loading".
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);

  const fileRef = useRef<HTMLInputElement>(null);
  const askRef = useRef<HTMLInputElement>(null);
  const hasMaterial = materials.length > 0;

  const loadSessions = useCallback(() => {
    return listSessions(courseId)
      .then((res) => {
        setSessions(res.sessions);
        setHistoryError("");
      })
      .catch((err) => {
        setSessions([]);
        setHistoryError(
          err instanceof Error ? err.message : "Could not load your chats.",
        );
      });
  }, [courseId]);

  useEffect(() => {
    let cancelled = false;

    listSessions(courseId)
      .then((res) => {
        if (!cancelled) setSessions(res.sessions);
      })
      .catch((err) => {
        if (cancelled) return;
        setSessions([]);
        setHistoryError(
          err instanceof Error ? err.message : "Could not load your chats.",
        );
      });

    return () => {
      cancelled = true;
    };
  }, [courseId]);

  function newChat() {
    setResult(null);
    setError("");
    setAdded("");
    setOpened(new Set());
    setTab("overview");
    setActiveId(null);
    setHistoryOpen(false);
    askRef.current?.focus();
  }

  async function openSession(id: string) {
    if (opening) return;

    setOpening(id);
    setError("");
    setAdded("");

    try {
      const { session } = await getSession(id);

      setResult(session.result);
      setOpened(new Set());
      setTab("overview");
      setActiveId(id);
      setHistoryOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open that chat.");
    } finally {
      setOpening(null);
    }
  }

  async function removeSession(id: string) {
    try {
      await deleteSession(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete that chat.");
      return;
    }

    setSessions((list) => (list ?? []).filter((x) => x.id !== id));

    if (id === activeId) newChat();
  }

  async function submit(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading || !courseId) return;

    setLoading(true);
    setError("");
    setAdded("");
    setResult(null);
    setOpened(new Set());
    setTab("overview");
    setActiveId(null);
    setHistoryOpen(false);

    try {
      const res = await ask(courseId, trimmed);

      setResult(res);
      setActiveId(res.session_id ?? null);
      setInput("");
      loadSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleAttach(file: File | undefined) {
    if (!file || !courseId) return;

    setError("");
    setAdded("");

    if (!isSupportedFile(file.name)) {
      setError(`Only ${SUPPORTED_EXTENSIONS.join(", ")} files are supported.`);
      return;
    }

    setUploading(true);

    try {
      const res = await uploadMaterial(courseId, file);
      setAdded(`Added ${res.source} successfully.`);
      refreshMaterials();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That file could not be added.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function selectTab(id: TabId) {
    setTab(id);
    setOpened((prev) => new Set(prev).add(id));
  }

  /** A tab is reachable when its agent produced something for this query. */
  function tabIsFilled(id: TabId): boolean {
    if (id === "overview") return true;
    if (!result) return false;

    const agent = TAB_META[id].agent;
    if (!agent) return false;

    return result.agents[agent]?.success === true;
  }

  const tabs: TabItem<TabId>[] = TAB_ORDER.map((id) => {
    const filled = tabIsFilled(id);

    return {
      id,
      label: TAB_META[id].label,
      icon: TAB_META[id].icon,
      disabled: !filled,
      disabledReason: "Nothing was generated here for your last question",
      unseen: filled && id !== "overview" && !opened.has(id),
    };
  });

  const askDisabled = loading || uploading || !courseId;

  return (
    <PageShell>
      <PageHeader
        title={courseId || "Welcome"}
        description={
          courseId
            ? courseName === courseId
              ? undefined
              : courseName
            : "Add a subject to get started."
        }
        actions={
          courseId ? (
            <>
              {!materialsLoading && (
                <Tag>
                  {materials.length} {materials.length === 1 ? "file" : "files"}
                </Tag>
              )}
              <Button
                size="sm"
                icon={History}
                aria-expanded={historyOpen}
                onClick={() => setHistoryOpen((v) => !v)}
              >
                History{sessions && sessions.length > 0 ? ` (${sessions.length})` : ""}
              </Button>
              <Button
                size="sm"
                icon={SquarePen}
                disabled={!result && !error}
                onClick={newChat}
              >
                New chat
              </Button>
            </>
          ) : undefined
        }
      />

      {!courseId && (
        <EmptyState
          title="Add your first subject"
          action={
            <Button variant="primary" icon={Plus} onClick={promptAddCourse}>
              Add a subject
            </Button>
          }
        >
          A subject is one of your courses, like ECON3321. Add it, upload a
          syllabus or your notes, and then ask anything about it. Enter a code
          that already exists to join that subject instead.
        </EmptyState>
      )}

      {courseId && (
        <>
          {/* ---------------- History ---------------- */}
          {historyOpen && (
            <Panel
              title="Previous chats"
              subtitle={`Your past questions in ${courseId}, newest first.`}
              icon={History}
              flush
              className="mb-6"
            >
              {historyError ? (
                <p role="alert" className="p-5 text-ui text-red md:p-6">
                  {historyError}
                </p>
              ) : sessions === null ? (
                <div role="status" aria-label="Loading" className="space-y-3 p-5 md:p-6">
                  <Skeleton className="h-5 w-4/5" />
                  <Skeleton className="h-5 w-2/3" />
                </div>
              ) : sessions.length === 0 ? (
                <p className="p-5 text-ui text-ink-2 md:p-6">
                  Nothing here yet. Questions you ask in {courseId} are saved
                  and appear in this list.
                </p>
              ) : (
                <ul className="divide-y divide-rule">
                  {sessions.map((s) => (
                    <li
                      key={s.id}
                      className={
                        "flex items-center gap-1 pr-2 " +
                        (s.id === activeId ? "bg-hl-soft" : "")
                      }
                    >
                      <button
                        type="button"
                        onClick={() => openSession(s.id)}
                        disabled={opening !== null}
                        aria-current={s.id === activeId ? "true" : undefined}
                        className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3 text-left transition-colors duration-150 hover:bg-sheet-2 disabled:opacity-60 md:px-6"
                      >
                        <span className="truncate text-body text-ink">
                          {s.title}
                        </span>
                        <span className="shrink-0 text-meta text-ink-3">
                          {opening === s.id ? "Opening…" : sessionDate(s.created_at)}
                        </span>
                      </button>
                      <IconButton
                        icon={Trash2}
                        label={`Delete chat: ${s.title}`}
                        onClick={() => removeSession(s.id)}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          )}

          {/* ---------------- Ask ---------------- */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(input);
            }}
            className="mb-6"
          >
            <label htmlFor="ask" className="sr-only">
              Ask a question about {courseName}
            </label>

            <div className="flex gap-2">
              <input
                ref={fileRef}
                type="file"
                accept={UPLOAD_ACCEPT}
                className="hidden"
                onChange={(e) => handleAttach(e.target.files?.[0])}
              />

              <IconButton
                icon={uploading ? Loader2 : Paperclip}
                label={`Upload course material (${SUPPORTED_EXTENSIONS.join(", ")})`}
                disabled={askDisabled}
                onClick={() => fileRef.current?.click()}
                className={
                  "size-12 border border-line bg-sheet hover:bg-sheet-2" +
                  (uploading ? " [&_svg]:animate-spin" : "")
                }
              />

              <TextInput
                id="ask"
                ref={askRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={askDisabled}
                placeholder={
                  uploading
                    ? "Reading your file…"
                    : loading
                      ? "Working on your question…"
                      : `Ask anything about ${courseName}`
                }
                className="h-12 flex-1"
              />

              <Button
                type="submit"
                variant="primary"
                icon={Send}
                loading={loading}
                disabled={askDisabled || !input.trim()}
                className="h-12 px-5"
              >
                Ask
              </Button>
            </div>

            {!result && !loading && hasMaterial && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-meta text-ink-2">Try</span>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => submit(s)}
                    className="rounded-tag border border-rule bg-sheet px-2.5 py-1 text-ui text-ink-2 transition-colors duration-150 hover:border-line hover:bg-sheet-2 hover:text-ink"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </form>

          {error && (
            <Notice tone="error" title="That didn't work" className="mb-6">
              {error}
            </Notice>
          )}

          {added && (
            <Notice tone="ok" className="mb-6">
              {added}
            </Notice>
          )}

          {/* ---------------- Results ---------------- */}
          {loading && (
            <Panel title="Working through your question" className="mb-8">
              <div role="status" aria-label="Working" className="space-y-3">
                <Skeleton className="h-5 w-11/12" />
                <Skeleton className="h-5 w-4/5" />
                <Skeleton className="h-5 w-2/3" />
              </div>
              <p className="mt-5 text-ui text-ink-2">
                Finding the right parts of your material, then writing a plan,
                an answer and practice questions. This usually takes a few
                seconds.
              </p>
            </Panel>
          )}

          {!loading && result && (
            <div className="mb-8 space-y-4">
              <Tabs
                label="Results"
                items={tabs}
                value={tab}
                onChange={selectTab}
              />

              {tab === "overview" && (
                <OverviewPanel result={result} onJumpToTab={selectTab} />
              )}

              {tab === "study" && result.agents.study?.success && (
                <StudyPanel data={result.agents.study.response} />
              )}

              {tab === "assessment" && result.agents.quiz?.success && (
                <QuizPanel
                  data={result.agents.quiz.response}
                  courseId={courseId}
                  topic={result.query}
                />
              )}

              {tab === "faq" && result.agents.faq?.success && (
                <FaqPanel
                  data={result.agents.faq.response}
                  question={result.query}
                />
              )}
            </div>
          )}

          <MaterialsTable
            key={courseId}
            courseId={courseId}
            role={role}
            materials={materials}
            loading={materialsLoading}
            onUpload={() => fileRef.current?.click()}
            onChanged={refreshMaterials}
          />
        </>
      )}
    </PageShell>
  );
}
