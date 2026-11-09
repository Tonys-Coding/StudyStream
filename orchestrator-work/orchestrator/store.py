"""
Courses, enrollments, activity and the dashboard.

These live in the three tables DATABASE_MIGRATION.sql creates. If that has
not been run, every function here fails with a 501 that says so, rather than
a database error the student cannot act on.
"""

import re
import secrets
import sys
from datetime import date
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import STAFF_ROLES, is_uuid, supabase


COURSE_ID_RE = re.compile(r"^[A-Z]{2,6}[0-9]{3,5}[A-Z]?$")

# The operator's instruction goes to the server log; the student gets a
# plain message.
MIGRATION_HINT = "This part of StudyStream isn't available yet. Please try again later."

MIGRATION_LOG = (
    "[ORCHESTRATOR] The database is missing tables. Run DATABASE_MIGRATION.sql "
    "once in the Supabase SQL editor, then reload."
)


@contextmanager
def migration_guard():
    """Turns 'table does not exist' into an instruction."""

    try:
        yield

    except HTTPException:
        raise

    except Exception as e:

        text = str(e)

        # PGRST205 is PostgREST's "no such table". A missing column or a
        # missing relationship is a different problem and should stay visible
        # as one rather than being reported as "run the migration".
        # 42703 is "no such column": the courses.visibility column from the
        # latest migration is missing.
        if (
            "PGRST205" in text
            or "42703" in text
            or ("relation" in text and "does not exist" in text)
            or ("column" in text and "does not exist" in text)
        ):
            print(MIGRATION_LOG)
            raise HTTPException(status_code=501, detail=MIGRATION_HINT)

        raise


def normalize_course_id(raw: str) -> str:
    return re.sub(r"\s+", "", (raw or "").strip().upper())


# -------------------------
# Courses
# -------------------------

# courses.visibility arrives with the latest migration. Until it has been run
# the app keeps working with private subjects only, instead of failing.
_has_visibility = False


def has_visibility() -> bool:
    """Only a positive answer is cached, so running the migration takes effect
    without restarting the server."""

    global _has_visibility

    if _has_visibility:
        return True

    try:
        supabase().table("courses").select("visibility").limit(1).execute()
        _has_visibility = True
    except Exception:
        return False

    return True


def _course_cols() -> str:
    return "id,name,created_by,visibility" if has_visibility() else "id,name,created_by"


def linked_teacher_ids(user_id: str) -> list[str]:
    """
    Teachers whose code this user has entered. If the teacher tables are not
    there yet this is simply empty, so the sidebar still works.
    """

    try:
        rows = supabase().table("teacher_links") \
            .select("teacher_id") \
            .eq("student_id", user_id) \
            .execute().data or []
    except Exception:
        return []

    return [r["teacher_id"] for r in rows]


def list_my_courses(user_id: str) -> list[dict]:
    """
    The subjects this user works in: the ones they added (or made), then the
    public ones made by teachers whose code they have entered.

    Each is {id, name, public, shared, teacher}. `shared` marks a public
    subject someone else made, which the sidebar lists under "Shared".
    """

    with migration_guard():

        rows = supabase().table("enrollments") \
            .select("course_id") \
            .eq("student_id", user_id) \
            .order("id") \
            .execute().data or []

        # Without a unique constraint the same subject could be stored twice.
        ids = list(dict.fromkeys(r["course_id"] for r in rows))

        found: dict[str, dict] = {}

        if ids:
            for c in supabase().table("courses") \
                    .select(_course_cols()) \
                    .in_("id", ids) \
                    .execute().data or []:
                found[c["id"]] = c

        # A teacher's public subjects reach only the students who entered
        # that teacher's code.
        public = []
        teachers = linked_teacher_ids(user_id)

        if teachers and has_visibility():
            public = supabase().table("courses") \
                .select(_course_cols()) \
                .eq("visibility", "public") \
                .in_("created_by", teachers) \
                .execute().data or []

        order = list(ids)

        for c in public:
            found.setdefault(c["id"], c)

            # A teacher's own public subject is already theirs, in `ids` or
            # deliberately removed; it is not "shared" with them.
            if c["id"] not in order and c.get("created_by") != user_id:
                order.append(c["id"])

        makers = {
            c["created_by"] for c in found.values()
            if c.get("visibility") == "public" and c.get("created_by")
        }

        teacher_names: dict[str, str] = {}

        if makers:
            teacher_names = {
                p["id"]: p["full_name"]
                for p in supabase().table("profiles")
                .select("id,full_name")
                .in_("id", list(makers))
                .execute().data or []
            }

    out = []

    for i in order:

        c = found.get(i) or {"id": i, "name": i}
        is_public = c.get("visibility") == "public"
        shared = is_public and c.get("created_by") != user_id

        out.append({
            "id": i,
            "name": c.get("name") or i,
            "public": is_public,
            "shared": shared,
            "teacher": teacher_names.get(c.get("created_by")) if shared else None
        })

    return out


def add_course(
        user_id: str,
        raw_id: str,
        name: str | None,
        public: bool = False,
        role: str | None = None
) -> dict:
    """
    Adds a subject to the user's list, creating it if nobody has yet.

    An existing course keeps the name and visibility it was created with, so
    two people typing different things for the same code do not fight over
    it. Only a teacher can create a public one.
    """

    course_id = normalize_course_id(raw_id)

    if not COURSE_ID_RE.match(course_id):
        raise HTTPException(
            status_code=400,
            detail="Use a course code like ECON3321."
        )

    if public and role != "teacher":
        raise HTTPException(
            status_code=403,
            detail="Only teachers can make a subject public."
        )

    if public and not has_visibility():
        raise HTTPException(status_code=501, detail=MIGRATION_HINT)

    with migration_guard():

        existing = supabase().table("courses") \
            .select(_course_cols()) \
            .eq("id", course_id) \
            .execute().data

        if existing:
            course = existing[0]
        else:
            course = {
                "id": course_id,
                "name": ((name or "").strip()[:60]) or course_id
            }

            if has_visibility():
                course["visibility"] = "public" if public else "private"

            supabase().table("courses").upsert(
                {**course, "created_by": user_id},
                on_conflict="id",
                ignore_duplicates=True
            ).execute()

            course["created_by"] = user_id

        if not is_enrolled(user_id, course_id):
            supabase().table("enrollments").insert({
                "student_id": user_id,
                "course_id": course_id
            }).execute()

    is_public = course.get("visibility") == "public"

    return {
        "id": course["id"],
        "name": course["name"],
        "public": is_public,
        "shared": is_public and course.get("created_by") != user_id,
        "teacher": None
    }


def remove_course(user_id: str, course_id: str) -> None:
    """Removes the subject from this user's list. Uploaded files are kept."""

    with migration_guard():

        supabase().table("enrollments") \
            .delete() \
            .eq("student_id", user_id) \
            .eq("course_id", course_id) \
            .execute()


def ensure_access(user_id: str, course_id: str) -> bool:
    """
    Whether this user may work in the subject. A public subject is open to its
    teacher and to anyone who entered that teacher's code, and the first time
    they use it they are enrolled, so a teacher's class numbers count the
    students who actually use it.
    """

    if is_enrolled(user_id, course_id):
        return True

    if not has_visibility():
        return False

    with migration_guard():

        rows = supabase().table("courses") \
            .select("id,created_by") \
            .eq("id", course_id) \
            .eq("visibility", "public") \
            .limit(1) \
            .execute().data

        if not rows:
            return False

        maker = rows[0].get("created_by")

        if maker != user_id and maker not in linked_teacher_ids(user_id):
            return False

        supabase().table("enrollments").insert({
            "student_id": user_id,
            "course_id": course_id
        }).execute()

    return True


def is_enrolled(user_id: str, course_id: str) -> bool:

    with migration_guard():

        rows = supabase().table("enrollments") \
            .select("id") \
            .eq("student_id", user_id) \
            .eq("course_id", course_id) \
            .limit(1) \
            .execute().data

    return bool(rows)


# -------------------------
# Activity
# -------------------------

def log_ask(user_id: str, course_id: str, message: str) -> None:
    """Best effort: a failed log line must never fail the student's answer."""

    if not is_uuid(user_id):
        return

    try:
        supabase().table("activity").insert({
            "user_id": user_id,
            "course_id": course_id,
            "kind": "ask",
            "message": message[:500]
        }).execute()

    except Exception as e:
        print("[ORCHESTRATOR] Could not log activity:", type(e).__name__)


def log_quiz(
        user_id: str,
        course_id: str,
        topic: str,
        score: int,
        total: int
) -> None:

    with migration_guard():

        supabase().table("activity").insert({
            "user_id": user_id,
            "course_id": course_id,
            "kind": "quiz",
            "message": topic[:500],
            "score": score,
            "total": total
        }).execute()


# -------------------------
# Dashboard
# -------------------------

def _pct(score: int, total: int) -> int | None:
    return round(100 * score / total) if total else None


def _summarize(rows: list[dict]) -> dict:
    """Question and quiz totals for a set of activity rows."""

    quizzes = [r for r in rows if r["kind"] == "quiz" and r.get("total")]

    return {
        "questions": sum(1 for r in rows if r["kind"] == "ask"),
        "quizzes": len(quizzes),
        "avg_score_pct": _pct(
            sum(r["score"] or 0 for r in quizzes),
            sum(r["total"] for r in quizzes)
        )
    }


def _material_counts(course_ids: list[str], user_id: str) -> dict[str, int]:
    """Distinct files per course that this user can see."""

    if not course_ids:
        return {}

    def query():
        return supabase().table("course_materials") \
            .select("course_id,source") \
            .in_("course_id", course_ids) \
            .or_(
                "visibility.eq.class,"
                f"and(visibility.eq.private,uploaded_by.eq.{user_id})"
            )

    files: dict[str, set] = {c: set() for c in course_ids}
    start = 0

    while True:
        batch = query().range(start, start + 999).execute().data or []

        for row in batch:
            files[row["course_id"]].add(row["source"])

        if len(batch) < 1000:
            break

        start += 1000

    return {c: len(s) for c, s in files.items()}


def build_dashboard(user_id: str, role: str | None) -> dict:
    """
    What the Dashboard shows.

    Everyone sees their own numbers. Teachers also get class-wide
    totals for the subjects they are in. Those are counts only: no student's
    questions or scores are listed individually.
    """

    courses = list_my_courses(user_id)
    ids = [c["id"] for c in courses]

    with migration_guard():

        mine = supabase().table("activity") \
            .select("kind,course_id,message,score,total,created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(500) \
            .execute().data or []

    materials = _material_counts(ids, user_id) if is_uuid(user_id) else {}

    per_course = []

    for course in courses:

        rows = [r for r in mine if r["course_id"] == course["id"]]

        per_course.append({
            **course,
            **_summarize(rows),
            "materials": materials.get(course["id"], 0)
        })

    result = {
        "success": True,
        "role": role,
        "totals": _summarize(mine),
        "courses": per_course,
        "recent": mine[:8],
        "class_stats": None
    }

    # Class totals are for subjects the teacher belongs to, not for every
    # public subject someone else made.
    ids = [c["id"] for c in courses if not c["shared"]]

    if role == "teacher" and ids:

        with migration_guard():

            everyone = supabase().table("activity") \
                .select("user_id,kind,course_id,score,total") \
                .in_("course_id", ids) \
                .limit(5000) \
                .execute().data or []

            members = supabase().table("enrollments") \
                .select("course_id,student_id") \
                .in_("course_id", ids) \
                .limit(5000) \
                .execute().data or []

        # Distinct students: the table has no unique constraint to rely on.
        enrolled: dict[str, int] = {}

        for course_id in ids:
            enrolled[course_id] = len({
                m["student_id"] for m in members if m["course_id"] == course_id
            })

        result["class_stats"] = [
            {
                **course,
                "enrolled": enrolled.get(course["id"], 0),
                "active": len({
                    r["user_id"] for r in everyone
                    if r["course_id"] == course["id"]
                }),
                **_summarize(
                    [r for r in everyone if r["course_id"] == course["id"]]
                )
            }
            for course in courses if not course["shared"]
        ]

    return result



# -------------------------
# Chat sessions
# -------------------------
#
# One session is one question and everything the agents answered, stored as
# the same JSON the workspace already renders, so reopening it is exact.

SESSION_LIMIT = 50


def save_session(user_id: str, course_id: str, title: str, result: dict) -> str | None:
    """Best effort, like log_ask: a failed save must never fail the answer."""

    if not is_uuid(user_id):
        return None

    try:
        rows = supabase().table("chat_sessions").insert({
            "user_id": user_id,
            "course_id": course_id,
            "title": title.strip()[:200] or "Untitled question",
            "result": result
        }).execute().data

        return rows[0]["id"] if rows else None

    except Exception as e:
        print("[ORCHESTRATOR] Could not save chat session:", type(e).__name__)
        return None


def list_sessions(user_id: str, course_id: str) -> list[dict]:

    with migration_guard():

        return supabase().table("chat_sessions") \
            .select("id,title,created_at") \
            .eq("user_id", user_id) \
            .eq("course_id", course_id) \
            .order("created_at", desc=True) \
            .limit(SESSION_LIMIT) \
            .execute().data or []


def get_session(user_id: str, session_id: str) -> dict:

    if not is_uuid(session_id):
        raise HTTPException(status_code=404, detail="That chat was not found.")

    with migration_guard():

        rows = supabase().table("chat_sessions") \
            .select("id,course_id,title,result,created_at") \
            .eq("id", session_id) \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute().data

    if not rows:
        raise HTTPException(status_code=404, detail="That chat was not found.")

    return rows[0]


def delete_session(user_id: str, session_id: str) -> None:

    if not is_uuid(session_id):
        raise HTTPException(status_code=404, detail="That chat was not found.")

    with migration_guard():

        supabase().table("chat_sessions") \
            .delete() \
            .eq("id", session_id) \
            .eq("user_id", user_id) \
            .execute()


# -------------------------
# Assignments
# -------------------------

def _clean_due(value: str | None) -> str | None:
    """A date as YYYY-MM-DD, or None. Anything else is a 400, not a DB error."""

    if not value:
        return None

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Due date must look like 2026-12-31."
        )


def _clean_title(value: str | None) -> str:

    title = (value or "").strip()

    if not title or len(title) > 200:
        raise HTTPException(
            status_code=400,
            detail="Give the assignment a title (up to 200 characters)."
        )

    return title


def list_assignments(user_id: str) -> list[dict]:

    with migration_guard():

        return supabase().table("assignments") \
            .select("id,course_id,title,due_date,done,created_at") \
            .eq("user_id", user_id) \
            .order("done") \
            .order("due_date", desc=False, nullsfirst=False) \
            .order("id") \
            .execute().data or []


def add_assignment(
        user_id: str,
        title: str,
        course_id: str | None,
        due_date: str | None
) -> dict:

    row = {
        "user_id": user_id,
        "title": _clean_title(title),
        "course_id": course_id or None,
        "due_date": _clean_due(due_date)
    }

    with migration_guard():

        return supabase().table("assignments") \
            .insert(row).execute().data[0]


def update_assignment(user_id: str, assignment_id: int, changes: dict) -> dict:
    """`changes` holds only the fields the caller sent."""

    patch: dict = {}

    if "title" in changes:
        patch["title"] = _clean_title(changes["title"])

    if "due_date" in changes:
        patch["due_date"] = _clean_due(changes["due_date"])

    if "course_id" in changes:
        patch["course_id"] = changes["course_id"] or None

    if "done" in changes:
        patch["done"] = bool(changes["done"])

    if not patch:
        raise HTTPException(status_code=400, detail="Nothing to change.")

    with migration_guard():

        rows = supabase().table("assignments") \
            .update(patch) \
            .eq("id", assignment_id) \
            .eq("user_id", user_id) \
            .execute().data

    if not rows:
        raise HTTPException(status_code=404, detail="That assignment was not found.")

    return rows[0]


def delete_assignment(user_id: str, assignment_id: int) -> None:

    with migration_guard():

        supabase().table("assignments") \
            .delete() \
            .eq("id", assignment_id) \
            .eq("user_id", user_id) \
            .execute()



# -------------------------
# Teacher codes
# -------------------------
#
# A teacher has one personal code. A student or TA who enters it is linked to
# that teacher and sees the teacher's public subjects under "Shared".

# No 0/O or 1/I/L, so a code read aloud or off a slide is hard to mistype.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def _normalize_code(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (raw or "").upper())


def format_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def _email_of(user_id: str) -> str | None:

    try:
        return supabase().auth.admin.get_user_by_id(user_id).user.email
    except Exception:
        return None


def get_teacher_code(teacher_id: str) -> dict:
    """The teacher's code (made on first request) and how many are linked."""

    with migration_guard():

        rows = supabase().table("teacher_codes") \
            .select("code") \
            .eq("teacher_id", teacher_id) \
            .limit(1) \
            .execute().data

        if rows:
            code = rows[0]["code"]
        else:
            for _ in range(5):
                code = "".join(
                    secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH)
                )

                try:
                    supabase().table("teacher_codes").insert({
                        "teacher_id": teacher_id,
                        "code": code
                    }).execute()
                    break
                except Exception as e:
                    # Another request made one, or the code collided.
                    if "duplicate" not in str(e).lower() and "23505" not in str(e):
                        raise
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Could not make a code. Please try again."
                )

        linked = supabase().table("teacher_links") \
            .select("student_id") \
            .eq("teacher_id", teacher_id) \
            .execute().data or []

    return {"code": format_code(code), "students": len(linked)}


def _teacher_summary(teacher_id: str) -> dict:

    profile = supabase().table("profiles") \
        .select("full_name") \
        .eq("id", teacher_id) \
        .limit(1) \
        .execute().data

    subjects = []

    if has_visibility():
        subjects = supabase().table("courses") \
            .select("id,name") \
            .eq("created_by", teacher_id) \
            .eq("visibility", "public") \
            .execute().data or []

    return {
        "id": teacher_id,
        "full_name": profile[0]["full_name"] if profile else "Teacher",
        "email": _email_of(teacher_id),
        "subjects": subjects
    }


def link_teacher(user_id: str, role: str | None, raw_code: str) -> dict:
    """Links this user to the teacher who owns the code."""

    if role == "teacher":
        raise HTTPException(
            status_code=400,
            detail="Teachers share their own code. They do not enter one."
        )

    code = _normalize_code(raw_code)

    if len(code) != CODE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="A teacher code looks like ABCD-2345."
        )

    with migration_guard():

        found = supabase().table("teacher_codes") \
            .select("teacher_id") \
            .eq("code", code) \
            .limit(1) \
            .execute().data

        if not found:
            raise HTTPException(
                status_code=404,
                detail="That teacher code was not found. Check it and try again."
            )

        teacher_id = found[0]["teacher_id"]

        already = supabase().table("teacher_links") \
            .select("teacher_id") \
            .eq("student_id", user_id) \
            .eq("teacher_id", teacher_id) \
            .limit(1) \
            .execute().data

        if not already:
            supabase().table("teacher_links").insert({
                "student_id": user_id,
                "teacher_id": teacher_id
            }).execute()

        return _teacher_summary(teacher_id)


def list_teachers(user_id: str) -> list[dict]:

    with migration_guard():

        ids = list(dict.fromkeys(linked_teacher_ids_strict(user_id)))

        return [_teacher_summary(t) for t in ids]


def linked_teacher_ids_strict(user_id: str) -> list[str]:
    """Like linked_teacher_ids, but a missing table is an error to report."""

    rows = supabase().table("teacher_links") \
        .select("teacher_id") \
        .eq("student_id", user_id) \
        .execute().data or []

    return [r["teacher_id"] for r in rows]


def unlink_teacher(user_id: str, teacher_id: str) -> None:
    """
    Stops following a teacher. Access went with the link, so the student is
    also taken out of that teacher's public subjects (their own private
    uploads in them stay in the database but are no longer reachable).
    """

    with migration_guard():

        supabase().table("teacher_links") \
            .delete() \
            .eq("student_id", user_id) \
            .eq("teacher_id", teacher_id) \
            .execute()

        if has_visibility():

            theirs = [
                c["id"] for c in supabase().table("courses")
                .select("id")
                .eq("created_by", teacher_id)
                .eq("visibility", "public")
                .execute().data or []
            ]

            if theirs:
                supabase().table("enrollments") \
                    .delete() \
                    .eq("student_id", user_id) \
                    .in_("course_id", theirs) \
                    .execute()



def list_roster(teacher_id: str) -> list[dict]:
    """
    Who has entered this teacher's code: name, role and email, nothing more.
    Not their questions, scores or files.
    """

    with migration_guard():

        links = supabase().table("teacher_links") \
            .select("student_id") \
            .eq("teacher_id", teacher_id) \
            .execute().data or []

        ids = list(dict.fromkeys(r["student_id"] for r in links))

        if not ids:
            return []

        people = supabase().table("profiles") \
            .select("id,full_name,role") \
            .in_("id", ids) \
            .execute().data or []

    roster = [
        {
            "id": person["id"],
            "full_name": person["full_name"],
            "role": person["role"],
            "email": _email_of(person["id"])
        }
        for person in people
    ]

    return sorted(roster, key=lambda r: (r["full_name"] or "").lower())
