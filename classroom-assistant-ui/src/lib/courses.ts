// The student's subject list.
//
// There is no courses table in Supabase, so the list lives in localStorage.
// It is merged with whatever the backend reports as having material, so a
// course someone else uploaded to still shows up in a fresh browser.
//
// Note: quizzes additionally need the course in COURSE_DATA in
// assessment-agent/data.py. Study plans and FAQ only need uploaded material.

export interface Course {
  id: string;
  name: string;
}

export const DEFAULT_COURSES: Course[] = [
  { id: "HIST301", name: "Time Travel & Historical Paradoxes" },
  { id: "CS3354", name: "Software Engineering" },
  { id: "CS2336", name: "Computer Science II" },
];

const STORAGE_KEY = "studystream.courses";

export function loadCourses(): Course[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [...DEFAULT_COURSES];

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [...DEFAULT_COURSES];

    const clean = parsed.filter(
      (c): c is Course =>
        c && typeof c.id === "string" && typeof c.name === "string",
    );

    return clean.length > 0 ? clean : [...DEFAULT_COURSES];
  } catch {
    return [...DEFAULT_COURSES];
  }
}

export function saveCourses(courses: Course[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(courses));
  } catch {
    // Private browsing or a full quota. The list still works for this
    // session, it just will not survive a reload.
  }
}

/** Course ids look like ECON3321 — letters then digits, no spaces. */
export function normalizeCourseId(raw: string): string {
  return raw.trim().toUpperCase().replace(/\s+/g, "");
}

export function validateCourseId(
  id: string,
  existing: Course[],
): string | null {
  if (!id) return "Enter a course ID.";
  if (!/^[A-Z]{2,6}[0-9]{3,5}[A-Z]?$/.test(id))
    return "Use a code like ECON3321.";
  if (existing.some((c) => c.id === id)) return `${id} is already in your list.`;
  return null;
}

/**
 * Adds any course the backend knows about that is missing from the list, so
 * material uploaded elsewhere is never orphaned.
 */
export function mergeDiscovered(
  courses: Course[],
  discoveredIds: string[],
): Course[] {
  const known = new Set(courses.map((c) => c.id));
  const extra = discoveredIds
    .filter((id) => !known.has(id))
    .map((id) => ({ id, name: id }));

  return extra.length > 0 ? [...courses, ...extra] : courses;
}
