import { useCallback, useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { signOut } from "@/lib/auth";
import { useAuth } from "@/lib/AuthContext";
import {
  loadCourses,
  saveCourses,
  mergeDiscovered,
  normalizeCourseId,
  validateCourseId,
  type Course,
} from "@/lib/courses";
import { listCourses, listMaterials, type Material } from "@/lib/api";

/** Shape handed to routed children via <Outlet context=...>. */
export interface WorkspaceContext {
  courseId: string;
  courseName: string;
  materials: Material[];
  materialsLoading: boolean;
  refreshMaterials: () => void;
}

export default function Layout() {
  const navigate = useNavigate();
  const { session } = useAuth();

  const [courses, setCourses] = useState<Course[]>(() => loadCourses());
  const [courseId, setCourseId] = useState(() => loadCourses()[0]?.id ?? "");

  const [materials, setMaterials] = useState<Material[]>([]);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  const [adding, setAdding] = useState(false);
  const [newId, setNewId] = useState("");
  const [newName, setNewName] = useState("");
  const [addError, setAddError] = useState("");

  // Pull in any course that has material but is not in this browser's list.
  useEffect(() => {
    let cancelled = false;

    listCourses()
      .then((res) => {
        if (cancelled) return;

        setCourses((current) => {
          const merged = mergeDiscovered(
            current,
            res.courses.map((c) => c.course_id),
          );
          if (merged !== current) saveCourses(merged);
          return merged;
        });
      })
      .catch(() => {
        // Backend down. The local list still works.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Bumping this re-runs the fetch, e.g. after an upload or a delete.
  const refreshMaterials = useCallback(() => setRefreshToken((t) => t + 1), []);

  // Loading is derived rather than stored, so the effect below never has to
  // call setState synchronously just to flip a flag.
  const materialsLoading = loadedFor !== courseId;

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
    navigate("/");
  }

  function addCourse(e: React.FormEvent) {
    e.preventDefault();

    const id = normalizeCourseId(newId);
    const problem = validateCourseId(id, courses);

    if (problem) {
      setAddError(problem);
      return;
    }

    const next = [...courses, { id, name: newName.trim() || id }];

    setCourses(next);
    saveCourses(next);
    setNewId("");
    setNewName("");
    setAddError("");
    setAdding(false);
    selectCourse(id);
  }

  /** Removes a subject from this list only. Uploaded material is untouched. */
  function removeCourse(id: string) {
    const next = courses.filter((c) => c.id !== id);

    setCourses(next);
    saveCourses(next);

    if (courseId === id && next.length > 0) {
      setCourseId(next[0].id);
    }
  }

  const activeCourse = courses.find((c) => c.id === courseId);

  return (
    <div className="bg-background h-screen overflow-hidden text-on-surface font-body-md flex">
      {/* ---------------- Sidebar ---------------- */}
      <aside className="hidden md:flex flex-col h-full py-margin-desktop px-4 w-64 glass-panel border-r border-chalkboard-border/50 shrink-0 z-20">
        <div className="mb-8 shrink-0">
          <h1 className="font-display-lg text-headline-lg text-primary tracking-tight">
            StudyStream
          </h1>
          <p className="font-label-sm text-label-sm text-on-surface-variant uppercase mt-1">
            Academic Workspace
          </p>
        </div>

        <div className="flex items-center justify-between px-4 mb-2 shrink-0">
          <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">
            Subjects
          </p>
          <button
            onClick={() => {
              setAdding((v) => !v);
              setAddError("");
            }}
            title="Add a subject"
            className="text-primary hover:bg-surface-container rounded-full p-1 transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">
              {adding ? "close" : "add"}
            </span>
          </button>
        </div>

        {adding && (
          <form onSubmit={addCourse} className="px-1 mb-3 shrink-0">
            <input
              autoFocus
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              placeholder="ECON3321"
              maxLength={12}
              className="w-full border border-chalkboard-border rounded-lg px-3 py-2 text-body-md mb-2 focus:outline-none focus:border-primary"
            />
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Course name (optional)"
              maxLength={60}
              className="w-full border border-chalkboard-border rounded-lg px-3 py-2 text-label-sm mb-2 focus:outline-none focus:border-primary"
            />

            {addError && (
              <p className="text-label-sm text-error mb-2">{addError}</p>
            )}

            <button
              type="submit"
              className="w-full py-2 bg-primary text-on-primary rounded-full text-label-sm font-medium hover:bg-on-primary-fixed-variant transition-colors"
            >
              Add subject
            </button>
          </form>
        )}

        <nav className="space-y-1 overflow-y-auto min-h-0 flex-1">
          {courses.map((course) => {
            const active = course.id === courseId;

            return (
              <div key={course.id} className="group relative">
                <button
                  onClick={() => selectCourse(course.id)}
                  title={course.name}
                  className={`w-full flex items-center gap-3 pl-4 pr-9 py-3 rounded-xl font-title-md text-title-md transition-colors cursor-pointer active:scale-95 duration-150 text-left ${
                    active
                      ? "bg-academy-blue-light text-primary"
                      : "text-on-surface-variant hover:bg-surface-container"
                  }`}
                >
                  <span className="material-symbols-outlined shrink-0">
                    {active ? "folder_open" : "folder"}
                  </span>
                  <span className="truncate">{course.id}</span>
                </button>

                {courses.length > 1 && (
                  <button
                    onClick={() => removeCourse(course.id)}
                    title="Remove from your subjects (uploaded files are kept)"
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full text-on-surface-variant opacity-0 group-hover:opacity-100 hover:bg-surface-container hover:text-error transition-opacity"
                  >
                    <span className="material-symbols-outlined text-[18px]">
                      close
                    </span>
                  </button>
                )}
              </div>
            );
          })}
        </nav>

        <div className="mt-4 pt-4 border-t border-chalkboard-border shrink-0">
          <div className="flex items-center gap-3 mb-2 px-1">
            <div className="w-10 h-10 rounded-full bg-academy-blue-light text-primary flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined">person</span>
            </div>
            <div className="min-w-0">
              <p className="font-title-md text-title-md text-on-surface">
                Student
              </p>
              <p className="text-label-sm text-on-surface-variant truncate">
                {session?.user.email}
              </p>
            </div>
          </div>

          <button
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-4 py-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition-colors text-label-sm"
          >
            <span className="material-symbols-outlined">logout</span>
            Sign out
          </button>
        </div>
      </aside>

      <Outlet
        context={
          {
            courseId,
            courseName: activeCourse?.name ?? courseId,
            materials,
            materialsLoading,
            refreshMaterials,
          } satisfies WorkspaceContext
        }
      />
    </div>
  );
}
