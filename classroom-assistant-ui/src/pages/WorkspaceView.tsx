import { useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  ask,
  isSupportedFile,
  uploadMaterial,
  SUPPORTED_EXTENSIONS,
  UPLOAD_ACCEPT,
  type AskResponse,
} from "@/lib/api";
import type { WorkspaceContext } from "@/components/Layout";
import { TAB_META, TAB_ORDER, type TabId } from "@/components/panels/tabs";
import OverviewPanel from "@/components/panels/OverviewPanel";
import StudyPanel from "@/components/panels/StudyPanel";
import QuizPanel from "@/components/panels/QuizPanel";
import FaqPanel from "@/components/panels/FaqPanel";
import MaterialsTable from "@/components/panels/MaterialsTable";

const SUGGESTIONS = [
  "Help me get ready for the midterm",
  "What is the grading breakdown?",
  "Quiz me on the main concepts",
];

export default function WorkspaceView() {
  const { courseId, courseName, materials, materialsLoading, refreshMaterials } =
    useOutletContext<WorkspaceContext>();

  const [input, setInput] = useState("");
  const [tab, setTab] = useState<TabId>("overview");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const hasMaterial = materials.length > 0;

  async function submit(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError("");
    setResult(null);
    setTab("overview");

    try {
      setResult(await ask(courseId, trimmed));
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleAttach(file: File | undefined) {
    if (!file) return;

    setError("");

    if (!isSupportedFile(file.name)) {
      setError(`Only ${SUPPORTED_EXTENSIONS.join(", ")} files are supported.`);
      return;
    }

    setUploading(true);

    try {
      await uploadMaterial(courseId, file);
      refreshMaterials();
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  /** A tab is reachable when its agent produced something for this query. */
  function tabIsFilled(id: TabId): boolean {
    if (id === "overview") return true;
    if (!result) return false;

    const agent = TAB_META[id].agent;
    if (!agent) return false;

    return result.agents[agent]?.success === true;
  }

  return (
    <main className="flex-1 flex flex-col h-full overflow-hidden">
      {/* ---------------- Tabs ---------------- */}
      <header className="w-full glass-panel border-b border-chalkboard-border z-10 px-6 md:px-margin-desktop h-16 flex items-center justify-between gap-4 shrink-0">
        {/* min-w-0 lets this shrink below its content width, so the tab strip
            scrolls instead of overrunning the course label beside it. */}
        <div className="flex items-center gap-1 md:gap-4 h-full overflow-x-auto min-w-0">
          {TAB_ORDER.map((id) => {
            const meta = TAB_META[id];
            const active = tab === id;
            const filled = tabIsFilled(id);

            return (
              <button
                key={id}
                onClick={() => filled && setTab(id)}
                disabled={!filled}
                title={
                  filled
                    ? meta.blurb
                    : "Nothing was generated here for your last question"
                }
                className={`h-full px-3 md:px-4 font-title-md text-title-md flex items-center gap-2 whitespace-nowrap transition-colors border-b-2 ${
                  active
                    ? "text-primary border-primary"
                    : filled
                      ? "text-on-surface-variant border-transparent hover:text-primary hover:bg-surface-container-low"
                      : "text-outline/40 border-transparent cursor-not-allowed"
                }`}
              >
                <span className="material-symbols-outlined text-[20px]">
                  {meta.icon}
                </span>
                {meta.label}
                {filled && !active && id !== "overview" && (
                  <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
                )}
              </button>
            );
          })}
        </div>

        <div className="hidden lg:flex items-center gap-2 shrink-0">
          <span className="material-symbols-outlined text-on-surface-variant text-[20px]">
            book
          </span>
          <span className="text-label-sm text-on-surface-variant">
            {courseName === courseId ? courseId : `${courseId} — ${courseName}`}
          </span>
        </div>
      </header>

      {/* ---------------- Content ----------------
          min-h-0 is what lets this actually scroll inside the flex column
          instead of pushing the chat bar off screen. */}
      <div className="flex-1 min-h-0 overflow-y-auto p-6 md:p-margin-desktop">
        <div className="max-w-7xl mx-auto">
          {error && (
            <div className="rounded-xl border border-error/40 bg-error-container/50 p-5 mb-8">
              <div className="flex items-center gap-2 mb-1">
                <span className="material-symbols-outlined text-error">
                  error
                </span>
                <h2 className="font-title-md text-title-md text-on-error-container">
                  That didn't work
                </h2>
              </div>
              <p className="text-body-md text-on-surface-variant">{error}</p>
            </div>
          )}

          {loading && <LoadingState />}

          {!loading && tab === "overview" && (
            <>
              {result ? (
                <OverviewPanel result={result} onJumpToTab={setTab} />
              ) : (
                !error && (
                  <EmptyState
                    courseLabel={courseName}
                    hasMaterial={materialsLoading || hasMaterial}
                    onPick={submit}
                  />
                )
              )}

              <MaterialsTable
                key={courseId}
                courseId={courseId}
                courseName={courseName}
                materials={materials}
                loading={materialsLoading}
                onUpload={() => fileRef.current?.click()}
                onChanged={refreshMaterials}
              />
            </>
          )}

          {!loading && result && (
            <>
              {tab === "study" && result.agents.study?.success && (
                <StudyPanel data={result.agents.study.response} />
              )}

              {tab === "assessment" && result.agents.quiz?.success && (
                <QuizPanel data={result.agents.quiz.response} />
              )}

              {tab === "faq" && result.agents.faq?.success && (
                <FaqPanel
                  data={result.agents.faq.response}
                  question={result.query}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* ---------------- Chat input ----------------
          A flex sibling rather than an overlay, so content can never end up
          hidden underneath it. */}
      <div className="shrink-0 border-t border-chalkboard-border/60 bg-surface/80 backdrop-blur-md px-4 py-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(input);
          }}
          className="max-w-4xl mx-auto paper-card rounded-full p-2 flex items-center gap-2 shadow-md"
        >
          <input
            ref={fileRef}
            type="file"
            accept={UPLOAD_ACCEPT}
            className="hidden"
            onChange={(e) => handleAttach(e.target.files?.[0])}
          />

          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading || loading}
            title={`Upload course material (${SUPPORTED_EXTENSIONS.join(", ")})`}
            className="p-3 text-on-surface-variant hover:text-primary transition-colors rounded-full hover:bg-surface-container disabled:opacity-40"
          >
            <span className="material-symbols-outlined">
              {uploading ? "hourglass_top" : "attach_file"}
            </span>
          </button>

          <input
            className="flex-1 min-w-0 bg-transparent border-none focus:ring-0 focus:outline-none text-body-md text-on-surface placeholder-outline px-2"
            placeholder={
              uploading
                ? "Reading and indexing your file…"
                : loading
                  ? "Working on your question…"
                  : `Ask anything about ${courseName}…`
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading || uploading}
            type="text"
          />

          <button
            type="submit"
            disabled={loading || uploading || !input.trim()}
            className="w-12 h-12 bg-primary text-on-primary rounded-full flex items-center justify-center hover:bg-on-primary-fixed-variant transition-colors shadow-sm active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            <span className="material-symbols-outlined filled">
              {loading ? "hourglass_top" : "send"}
            </span>
          </button>
        </form>
      </div>
    </main>
  );
}

function LoadingState() {
  return (
    <div className="paper-card rounded-xl p-8">
      <div className="flex items-center gap-3 mb-4">
        <span className="material-symbols-outlined filled text-primary text-[28px] animate-pulse">
          auto_awesome
        </span>
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Working through your question
        </h2>
      </div>
      <p className="font-body-notebook text-body-notebook text-on-surface-variant mb-6">
        Checking which assistants can help, then gathering their answers. This
        usually takes a few seconds.
      </p>
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-4 bg-surface-container rounded-full animate-pulse"
            style={{ width: `${90 - i * 18}%` }}
          />
        ))}
      </div>
    </div>
  );
}

function EmptyState({
  courseLabel,
  hasMaterial,
  onPick,
}: {
  courseLabel: string;
  hasMaterial: boolean;
  onPick: (q: string) => void;
}) {
  return (
    <div className="paper-card rounded-xl p-8">
      <div className="flex items-center gap-3 mb-4">
        <span className="material-symbols-outlined filled text-primary text-[28px]">
          auto_awesome
        </span>
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          {courseLabel}
        </h2>
      </div>

      <p className="font-body-notebook text-body-notebook text-on-surface-variant max-w-4xl leading-relaxed mb-6">
        Ask a question below and it goes to every assistant that can help. The
        summary lands here, and each assistant's full work appears in its own
        tab above.
      </p>

      {hasMaterial ? (
        <div className="flex gap-2 flex-wrap">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onPick(s)}
              className="px-4 py-2 bg-scholar-gold-muted text-secondary rounded-full font-label-sm text-label-sm border border-secondary/20 hover:border-secondary/50 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      ) : (
        <p className="text-body-md text-on-surface-variant">
          This subject has no material yet — upload something below to get
          started.
        </p>
      )}
    </div>
  );
}
