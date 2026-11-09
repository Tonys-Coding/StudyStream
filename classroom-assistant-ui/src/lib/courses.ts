// Subjects.
//
// The list itself lives in the database (see GET /courses), so it follows a
// student to any browser. This file only holds the shape and the checks the
// add-subject form runs before it bothers the server.

export interface Course {
  id: string;
  name: string;
  /** Visible to every student, made by a teacher or TA. */
  public?: boolean;
  /** A public subject someone else made. Listed under "Shared". */
  shared?: boolean;
  /** Who made a shared subject. */
  teacher?: string | null;
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
