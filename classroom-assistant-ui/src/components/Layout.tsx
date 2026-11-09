import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  FolderOpen,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareText,
  Plus,
  X,
} from "lucide-react";
import { signOut } from "@/lib/auth";
import { useAuth } from "@/lib/AuthContext";
import { useProfile } from "@/lib/ProfileContext";
import {
  normalizeCourseId,
  validateCourseId,
  type Course,
} from "@/lib/courses";
import {
  addCourse,
  leaveCourse,
  listCourses,
  listMaterials,
  type Material,
  type Role,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import Button, { IconButton } from "@/components/ui/Button";
import { Field, Switch, TextInput } from "@/components/ui/form";
import Wordmark from "@/components/Wordmark";

/** Shape handed to routed children via <Outlet context=...>. */
export interface WorkspaceContext {
  /** Empty until the student has added a subject. */
  courseId: string;
  courseName: string;
  materials: Material[];
  materialsLoading: boolean;
  refreshMaterials: () => void;
  role: Role | null;
  /** Opens the add-subject form in the sidebar (or drawer on a phone). */
  promptAddCourse: () => void;
  /** Reloads the sidebar's subjects, e.g. after entering a teacher code. */
  refreshCourses: () => void;
}

const ROLE_LABEL: Record<Role, string> = {
  student: "Student",
  teacher: "Teacher",
  ta: "TA",
};

export default function Layout() {
  const navigate = useNavigate();
  const { session } = useAuth();
  const { profile } = useProfile();

  const [courses, setCourses] = useState<Course[]>([]);
  const [coursesLoaded, setCoursesLoaded] = useState(false);
  const [coursesError, setCoursesError] = useState("");
  const [coursesToken, setCoursesToken] = useState(0);
  const [courseId, setCourseId] = useState("");

  const [materials, setMaterials] = useState<Material[]>([]);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [newId, setNewId] = useState("");
  const [newName, setNewName] = useState("");
  // Teachers and TAs choose whether a new subject is shown to every student.
  const [newPublic, setNewPublic] = useState(true);
  const [addError, setAddError] = useState("");

  const [drawerOpen, setDrawerOpen] = useState(false);

  // The subject list lives in the database so it follows the student around.
  useEffect(() => {
    let cancelled = false;

    listCourses()
      .then((res) => {
        if (cancelled) return;
        setCourses(res.courses);
        // Keep the current subject unless it has left the list (a teacher
        // was unlinked), in which case fall back to the first one.
        setCourseId((current) =>
          res.courses.some((c) => c.id === current)
            ? current
            : (res.courses[0]?.id ?? ""),
        );
        setCoursesLoaded(true);
      })
      .catch((err) => {
        if (cancelled) return;
        setCoursesError(
          err instanceof Error ? err.message : "Could not load your subjects.",
        );
        setCoursesLoaded(true);
      });

    return () => {
      cancelled = true;
    };
  }, [coursesToken]);

  const refreshCourses = useCallback(() => setCoursesToken((t) => t + 1), []);

  // Bumping this re-runs the fetch, e.g. after an upload or a delete.
  const refreshMaterials = useCallback(() => setRefreshToken((t) => t + 1), []);

  // Loading is derived rather than stored, so the effect below never has to
  // call setState synchronously just to flip a flag.
  const materialsLoading = courseId !== "" && loadedFor !== courseId;

  useEffect(() => {
    if (!courseId) return;

    let cancelled = false;

    listMaterials(courseId)
      .then((res) => {
        if (cancelled) return;
        setMaterials(res.materials);
        setLoadedFor(courseId);
      })
      .catch(() => {
        if (cancelled) return;
        // Backend unreachable. The workspace query surfaces the real error.
        setMaterials([]);
        setLoadedFor(courseId);
      });

    return () => {
      cancelled = true;
    };
  }, [courseId, refreshToken]);

  async function handleSignOut() {
    await signOut();
    navigate("/login", { replace: true });
  }

  /** Picking a subject always returns you to the workspace. */
  function selectCourse(id: string) {
    setCourseId(id);
    setDrawerOpen(false);
    navigate("/");
  }

  async function submitCourse(e: React.FormEvent) {
    e.preventDefault();

    const id = normalizeCourseId(newId);
    const problem = validateCourseId(id, courses);

    if (problem) {
      setAddError(problem);
      return;
    }

    setSaving(true);

    try {
      const { course } = await addCourse(
        id,
        newName.trim(),
        isTeacher && newPublic,
      );

      setCourses((current) => [...current, course]);
      setNewId("");
      setNewName("");
      setAddError("");
      setAdding(false);
      selectCourse(course.id);
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Could not add subject");
    } finally {
      setSaving(false);
    }
  }

  /** Removes a subject from this list only. Uploaded material is untouched. */
  async function removeCourse(id: string) {
    try {
      await leaveCourse(id);
    } catch (err) {
      setCoursesError(
        err instanceof Error ? err.message : "Could not remove subject",
      );
      return;
    }

    const next = courses.filter((c) => c.id !== id);

    setCourses(next);

    if (courseId === id) {
      setCourseId(next[0]?.id ?? "");
    }
  }

  function promptAddCourse() {
    setAdding(true);
    setAddError("");
    setDrawerOpen(true);
  }

  const activeCourse = courses.find((c) => c.id === courseId);
  const isTeacher = profile?.role === "teacher";

  const rail = (
    <RailBody
      courses={courses}
      coursesLoaded={coursesLoaded}
      coursesError={coursesError}
      courseId={courseId}
      adding={adding}
      saving={saving}
      newId={newId}
      newName={newName}
      newPublic={newPublic}
      isTeacher={isTeacher}
      addError={addError}
      onToggleAdding={() => {
        setAdding((v) => !v);
        setAddError("");
      }}
      onNewId={setNewId}
      onNewName={setNewName}
      onNewPublic={setNewPublic}
      onSubmitCourse={submitCourse}
      onSelect={selectCourse}
      onRemove={removeCourse}
      onNavigate={() => setDrawerOpen(false)}
      name={profile?.full_name || ROLE_LABEL[profile?.role ?? "student"]}
      roleLabel={profile?.role ? ROLE_LABEL[profile.role] : ""}
      email={session?.user.email ?? ""}
      onSignOut={handleSignOut}
    />
  );

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-paper text-ink md:flex-row">
      {/* ---------------- Phone top bar ---------------- */}
      <header className="z-30 flex h-14 shrink-0 items-center gap-2 bg-board px-3 text-chalk md:hidden">
        <IconButton
          icon={Menu}
          label="Open menu"
          onDark
          onClick={() => setDrawerOpen(true)}
        />
        <Wordmark size={28} className="[&>span]:text-lg" />
        {courseId && (
          <span className="ml-auto truncate text-meta font-medium text-chalk-2">
            {courseId}
          </span>
        )}
      </header>

      {/* ---------------- Rail (desktop) ---------------- */}
      <aside className="hidden h-full w-72 shrink-0 flex-col bg-board px-4 py-6 text-chalk md:flex">
        {rail}
      </aside>

      {/* ---------------- Drawer (phone) ---------------- */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <aside className="flex h-full w-80 max-w-[88vw] flex-col bg-board px-4 py-5 text-chalk shadow-pop">
            {rail}
          </aside>
          <button
            aria-label="Close menu"
            onClick={() => setDrawerOpen(false)}
            className="flex-1 bg-ink/40"
          />
        </div>
      )}

      <main className="min-h-0 min-w-0 relative flex-1 overflow-y-auto overscroll-contain">
        <Outlet
          context={
            {
              courseId,
              courseName: activeCourse?.name ?? courseId,
              materials,
              materialsLoading,
              refreshMaterials,
              role: profile?.role ?? null,
              promptAddCourse,
              refreshCourses,
            } satisfies WorkspaceContext
          }
        />
      </main>
    </div>
  );
}

interface RailProps {
  courses: Course[];
  coursesLoaded: boolean;
  coursesError: string;
  courseId: string;
  adding: boolean;
  saving: boolean;
  newId: string;
  newName: string;
  newPublic: boolean;
  isTeacher: boolean;
  addError: string;
  onToggleAdding: () => void;
  onNewId: (v: string) => void;
  onNewName: (v: string) => void;
  onNewPublic: (v: boolean) => void;
  onSubmitCourse: (e: React.FormEvent) => void;
  onSelect: (id: string) => void;
  onRemove: (id: string) => void;
  onNavigate: () => void;
  name: string;
  roleLabel: string;
  email: string;
  onSignOut: () => void;
}

/**
 * The rail's contents, shared by the desktop column and the phone drawer.
 * Whatever is current, a page or a subject, is highlighted with the marker.
 */
function RailBody(p: RailProps) {
  const initials = p.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");

  const mine = p.courses.filter((c) => !c.shared);
  const shared = p.courses.filter((c) => c.shared);

  /** One subject row. Shared ones cannot be removed: they belong to a teacher. */
  function renderCourse(course: Course) {
    const active = course.id === p.courseId;
    const named = course.name !== course.id ? course.name : "";
    const second = course.shared
      ? [named, course.teacher].filter(Boolean).join(" · ")
      : course.public
        ? `Public${named ? ` · ${named}` : ""}`
        : named;

    return (
      <div key={course.id} className="group relative">
        <button
          onClick={() => p.onSelect(course.id)}
          aria-current={active ? "true" : undefined}
          className={cn(
            "relative flex h-12 w-full items-center rounded-ctl pl-3 text-left transition-colors duration-150",
            course.shared ? "pr-3" : "pr-10",
            active
              ? "text-ink"
              : "text-chalk-2 hover:bg-board-2 hover:text-chalk",
          )}
        >
          {active && (
            <span
              aria-hidden
              className="swipe absolute inset-0 rounded-ctl bg-hl"
            />
          )}
          <span className="relative min-w-0">
            <span className="block text-ui font-semibold leading-tight">
              {course.id}
            </span>
            {second && (
              <span className="block truncate text-meta leading-tight opacity-85">
                {second}
              </span>
            )}
          </span>
        </button>

        {!course.shared && (
          /* Always shown on a phone, where there is no hover. */
          <IconButton
            icon={X}
            label={`Remove ${course.id} from your subjects (files are kept)`}
            onDark={!active}
            onClick={() => p.onRemove(course.id)}
            className={cn(
              "absolute right-1 top-1/2 size-8 -translate-y-1/2 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100",
              active && "text-ink hover:bg-ink/10 hover:text-ink",
            )}
          />
        )}
      </div>
    );
  }

  return (
    <>
      <div className="mb-7 hidden shrink-0 px-2 md:block">
        <Wordmark />
      </div>

      <nav aria-label="Pages" className="mb-6 shrink-0 space-y-1 pt-1 md:pt-0">
        <RailLink to="/" end icon={MessageSquareText} onClick={p.onNavigate}>
          Workspace
        </RailLink>
        <RailLink to="/dashboard" icon={LayoutDashboard} onClick={p.onNavigate}>
          Dashboard
        </RailLink>
        <RailLink to="/teachers" icon={GraduationCap} onClick={p.onNavigate}>
          {p.isTeacher ? "Your class" : "Teachers"}
        </RailLink>
      </nav>

      <div className="mb-1.5 flex shrink-0 items-center justify-between px-3">
        <h2 className="font-sans text-meta font-medium text-chalk-2">
          Subjects
        </h2>
        <IconButton
          icon={p.adding ? X : Plus}
          label={p.adding ? "Cancel" : "Add a subject"}
          onDark
          onClick={p.onToggleAdding}
          className="size-7"
        />
      </div>

      {p.adding && (
        <form
          onSubmit={p.onSubmitCourse}
          className="mb-3 shrink-0 space-y-3 rounded-ctl bg-board-2 p-3"
        >
          <div className="[&_label]:text-chalk [&_p]:text-chalk-2">
            <Field label="Course code" hint="Like ECON3321. A code that exists is joined.">
              {(id) => (
                <TextInput
                  id={id}
                  autoFocus
                  value={p.newId}
                  onChange={(e) => p.onNewId(e.target.value)}
                  placeholder="ECON3321"
                  maxLength={12}
                />
              )}
            </Field>
          </div>
          <div className="[&_label]:text-chalk">
            <Field label="Name (for a new course)">
              {(id) => (
                <TextInput
                  id={id}
                  value={p.newName}
                  onChange={(e) => p.onNewName(e.target.value)}
                  maxLength={60}
                />
              )}
            </Field>
          </div>

          {p.isTeacher && (
            <Switch
              checked={p.newPublic}
              onChange={p.onNewPublic}
              label={p.newPublic ? "Public" : "Private"}
              hint={
                p.newPublic
                  ? "Students who enter your teacher code see it under Shared."
                  : "Students join with the course code."
              }
            />
          )}

          {p.addError && (
            <p role="alert" className="rounded-tag bg-red-soft px-2 py-1.5 text-meta text-red">
              {p.addError}
            </p>
          )}

          <Button
            type="submit"
            variant="secondary"
            size="sm"
            loading={p.saving}
            className="w-full"
          >
            {p.saving ? "Adding" : "Add subject"}
          </Button>
        </form>
      )}

      {p.coursesError && (
        <p role="alert" className="mb-2 rounded-tag bg-red-soft px-3 py-2 text-meta text-red">
          {p.coursesError}
        </p>
      )}

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto">
        <nav aria-label="Subjects" className="space-y-1">
          {p.coursesLoaded && mine.length === 0 && !p.coursesError && (
            <p className="px-3 text-meta text-chalk-2">
              {shared.length > 0
                ? "Use + to add a subject by its code."
                : "No subjects yet. Use + to add one, or enter a code that already exists to join it."}
            </p>
          )}

          {mine.map((course) => renderCourse(course))}
        </nav>

        {shared.length > 0 && (
          <nav aria-label="Shared subjects" className="space-y-1">
            <h2 className="px-3 pb-0.5 font-sans text-meta font-medium text-chalk-2">
              Shared
            </h2>

            {shared.map((course) => renderCourse(course))}
          </nav>
        )}
      </div>

      <div className="mt-4 shrink-0 border-t border-board-3 pt-4">
        <div className="mb-2 flex items-center gap-3 px-1">
          <div
            aria-hidden
            className="flex size-10 shrink-0 items-center justify-center rounded-full bg-board-2 font-serif text-body font-semibold text-chalk"
          >
            {initials || "?"}
          </div>
          <div className="min-w-0">
            <p className="truncate text-ui font-medium text-chalk">{p.name}</p>
            <p className="truncate text-meta text-chalk-2">
              {p.roleLabel ? `${p.roleLabel} · ` : ""}
              {p.email}
            </p>
          </div>
        </div>

        <button
          onClick={p.onSignOut}
          className="flex h-10 w-full items-center gap-3 rounded-ctl px-3 text-ui text-chalk-2 transition-colors duration-150 hover:bg-board-2 hover:text-chalk"
        >
          <LogOut className="size-[18px]" aria-hidden />
          Sign out
        </button>
      </div>
    </>
  );
}

function RailLink({
  to,
  end,
  icon: Icon,
  onClick,
  children,
}: {
  to: string;
  end?: boolean;
  icon: typeof FolderOpen;
  onClick: () => void;
  children: string;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          "relative flex h-10 items-center gap-3 rounded-ctl px-3 text-ui font-medium transition-colors duration-150",
          isActive
            ? "text-ink"
            : "text-chalk-2 hover:bg-board-2 hover:text-chalk",
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span
              aria-hidden
              className="swipe absolute inset-0 rounded-ctl bg-hl"
            />
          )}
          <Icon className="relative size-[18px]" aria-hidden />
          <span className="relative">{children}</span>
        </>
      )}
    </NavLink>
  );
}
