"""
Offline checks for the code that has no network in it: JSON handling,
chunking, quiz validation and dashboard maths. Needs no running services and
no credentials.

    ../../.venv-1/bin/python test_units.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "orchestrator"))

# Importing these builds no client, but the modules read the environment.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "unused")

from common import ModelOutputError, chunk_text, is_uuid, parse_json  # noqa: E402


def load_agent(folder: str):
    """
    Loads one service's agent.py the way that service does: from its own
    folder, so its own prompts.py is the one it finds. Every service has an
    agent.py and a prompts.py, so they cannot all be on sys.path at once.
    """

    import importlib.util

    for name in ("prompts", "models"):
        sys.modules.pop(name, None)

    sys.path.insert(0, str(ROOT / folder))

    try:
        spec = importlib.util.spec_from_file_location(
            f"{folder}_agent", ROOT / folder / "agent.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(ROOT / folder))

    return module

passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   {detail}" if detail and not ok else ""))
    if ok:
        passed += 1
    else:
        failed += 1


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


# ---- parse_json -----------------------------------------------------------
check("plain JSON", parse_json('{"a": 1}') == {"a": 1})
check("code fenced", parse_json('```json\n{"a": 1}\n```') == {"a": 1})
check("fenced, no language", parse_json('```\n{"a": 1}\n```') == {"a": 1})
check("sentence around it", parse_json('Here you go: {"a": 1} Hope that helps!') == {"a": 1})
check("garbage raises", raises(lambda: parse_json("not json at all"), ModelOutputError))
check("empty raises", raises(lambda: parse_json(""), ModelOutputError))


# ---- chunk_text -----------------------------------------------------------
text = " ".join(f"Sentence number {i} is here." for i in range(400))
chunks = chunk_text(text, size=500, overlap=80)

check("chunks are produced", len(chunks) > 5, str(len(chunks)))
check("no chunk is wildly oversized", all(len(c) <= 520 for c in chunks),
      str(max(len(c) for c in chunks)))
check("chunks end on a sentence, not mid-word",
      all(c.endswith(".") for c in chunks[:-1]), repr(chunks[0][-20:]))
check("chunks overlap so ideas are not cut in half",
      chunks[1][:20] in chunks[0] or chunks[0][-60:].split(" ")[-3] in chunks[1])
check("no text is lost", all(f"number {i} " in " ".join(chunks) for i in (0, 199, 399)))
check("tiny text is one chunk", chunk_text("Short note.") == ["Short note."])
check("blank text is no chunks", chunk_text("   \n\n  ") == [])
check("one huge word does not loop forever", len(chunk_text("x" * 5000, size=500)) > 1)


# ---- is_uuid --------------------------------------------------------------
check("uuid accepted", is_uuid("6f9ae08e-3a5c-4d0f-9d6e-0b6a2f3c1d11"))
check("dev id rejected", not is_uuid("test-user"))
check("None rejected", not is_uuid(None))


# ---- quiz validation ------------------------------------------------------
assessment = load_agent("assessment-agent")
_clean_question = assessment._clean_question
_resolve_answer = assessment._resolve_answer
_validator = assessment._validator

good = {"question": "Q?", "choices": ["a", "b", "c", "d"], "answer": "b"}
q = _clean_question(good)
check("good question kept", q is not None and q["answer"] == "b")
check("answer stays correct after shuffling", q["answer"] in q["choices"])
check("answer repaired from letter", _resolve_answer("B", ["a", "b", "c", "d"]) == "b")
check("answer repaired from 'c)'", _resolve_answer("c)", ["a", "b", "c", "d"]) == "c")
check("answer repaired from case", _resolve_answer("B ", ["Apple", "b", "c", "d"]) == "b")
check("answer not in choices rejected", _clean_question({**good, "answer": "zebra"}) is None)
check("three choices rejected", _clean_question({**good, "choices": ["a", "b", "c"]}) is None)
check("duplicate choices rejected", _clean_question({**good, "choices": ["a", "a", "b", "c"]}) is None)
check("five choices rejected", _clean_question({**good, "choices": list("abcde")}) is None)
check("blank question rejected", _clean_question({**good, "question": "  "}) is None)
check("non-dict rejected", _clean_question("nope") is None)

validate = _validator(3)
check("invalid questions are dropped, valid kept",
      len(validate({"questions": [good, {"question": "x"}, good]})) == 2)
check("capped at the requested number", len(validate({"questions": [good] * 9})) == 3)
check("bare list accepted", len(validate([good])) == 1)
check("no usable questions raises", raises(lambda: validate({"questions": [{"x": 1}]}), ModelOutputError))
check("wrong shape raises", raises(lambda: validate({"questions": "nope"}), ModelOutputError))


# ---- study plan validation ------------------------------------------------
study = load_agent("study-agent")

ok_plan = study._validate({"study_plan": [" Read ch 1 ", "Do problems"], "focus_topics": ["A"], "estimated_hours": 5})
check("plan cleaned", ok_plan == {"study_plan": ["Read ch 1", "Do problems"], "focus_topics": ["A"], "estimated_hours": 5.0})
check("missing hours becomes null", study._validate({"study_plan": ["x"]})["estimated_hours"] is None)
check("negative hours becomes null", study._validate({"study_plan": ["x"], "estimated_hours": -3})["estimated_hours"] is None)
check("empty plan raises", raises(lambda: study._validate({"study_plan": []}), ModelOutputError))
check("raw JSON as a step is not accepted as a plan", raises(lambda: study._validate("{\"study_plan\": 1}"), ModelOutputError))


# ---- dashboard maths ------------------------------------------------------
import store  # noqa: E402

rows = [
    {"kind": "ask", "score": None, "total": None},
    {"kind": "ask", "score": None, "total": None},
    {"kind": "quiz", "score": 3, "total": 4},
    {"kind": "quiz", "score": 1, "total": 4},
]
s = store._summarize(rows)
check("question and quiz counts", s["questions"] == 2 and s["quizzes"] == 2)
check("average is points over points, not mean of percents", s["avg_score_pct"] == 50)
check("no quizzes gives no average", store._summarize([rows[0]])["avg_score_pct"] is None)
check("course ids normalised", store.normalize_course_id(" econ 3321 ") == "ECON3321")
check("good course id", bool(store.COURSE_ID_RE.match("ECON3321")))
check("bad course id", not store.COURSE_ID_RE.match("hello"))


# ---- /ask survives Azure failing around the agents -------------------------
import router  # noqa: E402


def boom(*a, **k):
    raise RuntimeError("azure is down")


router.call_faq_agent = lambda **k: {"success": True, "answer": "42", "sources": ["a.txt"]}
router.call_study_agent = lambda **k: {"success": True, "study_plan": ["x", "y"], "focus_topics": [], "estimated_hours": 1.0, "sources": []}

router.select_agents = boom
router.build_overview = boom

out = router.route_all("What is the grading breakdown?", "u", "HIST301")
check("agent selection failing falls back to keyword rules", out["selected_agents"] == ["faq"], str(out["selected_agents"]))
check("overview failing still returns the agents' work", out["agents"]["faq"]["success"] is True)
check("overview failing gives a plain summary", "answered" in out["overview"].lower(), out["overview"])

router.select_agents = lambda m: ["study", "faq"]
out = router.route_all("get ready", "u", "HIST301")
check("both agents run when selected", set(out["agents"]) == {"study", "faq"})
check("fallback overview counts steps", "2 steps" in out["overview"], out["overview"])

router.select_agents = lambda m: []
out = router.route_all("explain the syllabus", "u", "HIST301")
check("empty selection falls back to keyword rules", out["selected_agents"] == ["faq"], str(out["selected_agents"]))

router.select_agents = lambda m: ["study"]
out = router.route_all("give me a summary of my paper in simple words", "u", "HIST301")
check("the Answer agent always runs", "faq" in out["agents"], str(list(out["agents"])))
out = router.route_all("x", "u", "HIST301", agents=["study"])
check("but not when the caller names the agents", list(out["agents"]) == ["study"], str(list(out["agents"])))

qa = load_agent("assessment-agent")
q = qa._clean_question({"question": "Q?", "choices": ["a", "b", "c", "d"], "answer": "b", "explanation": " Because b. "})
check("a quiz question keeps its explanation", q and q["explanation"] == "Because b.")
q = qa._clean_question({"question": "Q?", "choices": ["a", "b", "c", "d"], "answer": "b"})
check("a missing explanation becomes empty, not an error", q and q["explanation"] == "")


# -------------------------
# Chat sessions and assignments, against an in-memory stand-in for Supabase
# -------------------------

print("\nSessions and assignments")

import store  # noqa: E402
from fastapi import HTTPException  # noqa: E402


class FakeQuery:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.op, self.payload, self.filters, self.max = "select", None, [], None

    def select(self, *_): self.op = "select"; return self
    def insert(self, row): self.op, self.payload = "insert", row; return self
    def update(self, row): self.op, self.payload = "update", row; return self
    def delete(self): self.op = "delete"; return self
    def eq(self, k, v): self.filters.append((k, v)); return self
    def in_(self, k, vs): self.filters.append((k, ("IN", list(vs)))); return self

    def upsert(self, row, **_):
        self.op, self.payload = "upsert", row
        return self
    def order(self, *a, **k): return self
    def limit(self, n): self.max = n; return self
    def or_(self, *_): return self
    def range(self, *_): return self

    def execute(self):
        rows = self.db.setdefault(self.name, [])
        def match(r, k, v):
            if isinstance(v, tuple) and v and v[0] == "IN":
                return r.get(k) in v[1]
            return r.get(k) == v

        hit = [r for r in rows if all(match(r, k, v) for k, v in self.filters)]

        class R: pass
        out = R()

        if self.op == "insert":
            row = dict(self.payload)
            row.setdefault("id", str(__import__("uuid").uuid4()) if self.name == "chat_sessions" else len(rows) + 1)
            row.setdefault("done", False)
            rows.append(row)
            out.data = [row]
        elif self.op == "upsert":
            if not any(r.get("id") == self.payload["id"] for r in rows):
                rows.append(dict(self.payload))
            out.data = []
        elif self.op == "update":
            for r in hit:
                r.update(self.payload)
            out.data = hit
        elif self.op == "delete":
            for r in hit:
                rows.remove(r)
            out.data = hit
        else:
            out.data = hit[: self.max] if self.max else hit

        return out


class FakeDB:
    def __init__(self): self.tables = {}
    def table(self, name): return FakeQuery(self.tables, name)


db = FakeDB()
store.supabase = lambda: db

ME = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def status_of(fn, *a, **k):
    try:
        fn(*a, **k)
        return 200
    except HTTPException as e:
        return e.status_code


sid = store.save_session(ME, "HIST301", "  What is on the midterm?  ", {"overview": "x"})
check("a chat is saved and returns its id", bool(sid))
check("saving trims the title", store.list_sessions(ME, "HIST301")[0]["title"] == "What is on the midterm?")
check("a chat can be reopened with its full result", store.get_session(ME, sid)["result"] == {"overview": "x"})
check("chats are listed per subject", store.list_sessions(ME, "CS3354") == [])
check("someone else cannot open my chat", status_of(store.get_session, OTHER, sid) == 404)
check("a made-up chat id is a 404, not an error", status_of(store.get_session, ME, "nope") == 404)
check("dev mode (no real user) saves nothing", store.save_session("test-user", "HIST301", "q", {}) is None)
store.delete_session(OTHER, sid)
check("someone else cannot delete my chat", len(store.list_sessions(ME, "HIST301")) == 1)
store.delete_session(ME, sid)
check("I can delete my chat", store.list_sessions(ME, "HIST301") == [])

a = store.add_assignment(ME, "  Essay draft ", "HIST301", "2026-12-01")
check("an assignment is added with a trimmed title", a["title"] == "Essay draft" and a["due_date"] == "2026-12-01")
check("an empty title is a 400", status_of(store.add_assignment, ME, "   ", None, None) == 400)
check("a bad date is a 400", status_of(store.add_assignment, ME, "x", None, "tomorrow") == 400)
check("no due date is allowed", store.add_assignment(ME, "Read ch. 3", None, None)["due_date"] is None)
check("assignments are private to their owner", store.list_assignments(OTHER) == [])
check("I can mark one done", store.update_assignment(ME, a["id"], {"done": True})["done"] is True)
check("only the fields sent change", store.update_assignment(ME, a["id"], {"title": "Essay v2"})["done"] is True)
check("an empty change is a 400", status_of(store.update_assignment, ME, a["id"], {}) == 400)
check("someone else cannot edit mine", status_of(store.update_assignment, OTHER, a["id"], {"done": False}) == 404)
store.delete_assignment(OTHER, a["id"])
check("someone else cannot delete mine", len(store.list_assignments(ME)) == 2)
store.delete_assignment(ME, a["id"])
check("I can delete mine", len(store.list_assignments(ME)) == 1)


print("\nTeachers, TAs and shared subjects")

db.tables.clear()
store._email_of = lambda i: "grace@utdallas.edu"
TEACHER = "33333333-3333-4333-8333-333333333333"
STUDENT = "44444444-4444-4444-8444-444444444444"
TA = "55555555-5555-4555-8555-555555555555"
db.tables["profiles"] = [{"id": TEACHER, "full_name": "Grace Hopper"}]

check("a student cannot make a public subject",
      status_of(store.add_course, STUDENT, "ECON3321", "Econ", True, "student") == 403)
check("a TA cannot make a public subject either",
      status_of(store.add_course, TA, "TA1001", "x", True, "ta") == 403)
check("a teacher can",
      status_of(store.add_course, TEACHER, "TA1001", "x", True, "teacher") == 200)

c = store.add_course(TEACHER, "HIST400", "Rome", True, "teacher")
check("a teacher's public subject is public, and not 'shared' for them", c["public"] and not c["shared"])
check("a teacher's subject is in their own list", [x["id"] for x in store.list_my_courses(TEACHER)].count("HIST400") == 1)

check("an unlinked student does not see a public subject",
      all(x["id"] != "HIST400" for x in store.list_my_courses(STUDENT)))
check("and cannot work in it", store.ensure_access(STUDENT, "HIST400") is False)

code = store.get_teacher_code(TEACHER)
check("a teacher gets a code like ABCD-2345", len(code["code"]) == 9 and code["code"][4] == "-", code["code"])
check("asking again returns the same code", store.get_teacher_code(TEACHER)["code"] == code["code"])
check("a new code starts with no students", code["students"] == 0)

check("a teacher cannot enter a code", status_of(store.link_teacher, TEACHER, "teacher", code["code"]) == 400)
check("a wrong code is a 404", status_of(store.link_teacher, STUDENT, "student", "ZZZZ-ZZZZ") == 404)
check("a malformed code is a 400", status_of(store.link_teacher, STUDENT, "student", "abc") == 400)

t = store.link_teacher(STUDENT, "student", code["code"].lower().replace("-", " "))
check("a code works in any case, with a space for the dash", t["id"] == TEACHER)
check("the summary has the teacher's name and email", t["full_name"] == "Grace Hopper" and t["email"] == "grace@utdallas.edu")
check("and lists their public subjects", {x["id"] for x in t["subjects"]} == {"TA1001", "HIST400"}, str(t["subjects"]))
store.link_teacher(STUDENT, "student", code["code"])
check("linking twice does not duplicate", len(store.list_teachers(STUDENT)) == 1)
check("the teacher sees how many are linked", store.get_teacher_code(TEACHER)["students"] == 1)

mine = store.list_my_courses(STUDENT)
shared = [x for x in mine if x["id"] == "HIST400"][0]
check("a linked student now sees the subject, marked shared", shared["shared"] and shared["teacher"] == "Grace Hopper", str(shared))
check("and can work in it", store.ensure_access(STUDENT, "HIST400") is True)
check("without being listed twice", [x["id"] for x in store.list_my_courses(STUDENT)].count("HIST400") == 1)

store.link_teacher(TA, "ta", code["code"])
check("a TA can link to a teacher too", len(store.list_teachers(TA)) == 1)

store.add_course(TEACHER, "CS9999", "Secret", False, "teacher")
check("a private subject is not shown to linked students", all(x["id"] != "CS9999" for x in store.list_my_courses(STUDENT)))
check("and they cannot work in it", store.ensure_access(STUDENT, "CS9999") is False)

db.tables["profiles"] += [
    {"id": STUDENT, "full_name": "Jordan Rivera", "role": "student"},
    {"id": TA, "full_name": "Alex Kim", "role": "ta"},
]
roster = store.list_roster(TEACHER)
check("the roster lists linked students and TAs by name", [r["full_name"] for r in roster] == ["Alex Kim", "Jordan Rivera"], str(roster))
check("with role and email", roster[0]["role"] == "ta" and roster[0]["email"] == "grace@utdallas.edu")
check("and nothing about their activity", set(roster[0]) == {"id", "full_name", "role", "email"})
check("a teacher with nobody linked has an empty roster", store.list_roster(TA) == [])

store.unlink_teacher(STUDENT, TEACHER)
check("unlinking removes the shared subject", all(not x["shared"] for x in store.list_my_courses(STUDENT)))
check("and the teacher from the list", store.list_teachers(STUDENT) == [])
check("a student's own subject is private",
      store.add_course(STUDENT, "ECON3321", "Econ", False, "student")["public"] is False)

# Class numbers belong to teachers, not TAs.
store.supabase = lambda: db
check("only teachers get class stats", store.build_dashboard(TA, "ta")["class_stats"] is None)

print(f"\n{passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
