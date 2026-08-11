import requests

BASE = "http://127.0.0.1:8001"
CHAT_URL = f"{BASE}/chat"
ASK_URL = f"{BASE}/ask"


# This script sends no Authorization header, so it needs REQUIRE_AUTH=false
# in orchestrator-work/.env.
TEST_USER_ID = "test-user"

# Must be a course that has material ingested in Supabase AND an entry in
# assessment-agent/data.py, or the study and FAQ agents will correctly 404.
TEST_COURSE_ID = "HIST301"

# Some tests need a course that has NO material but IS in COURSE_DATA, so the
# quiz agent succeeds while study and FAQ correctly 404. Which of these is
# empty changes as material gets uploaded, so pick one at runtime rather than
# hardcoding an assumption that quietly goes stale.
EMPTY_COURSE_CANDIDATES = ["CS3354", "CS2336"]


def find_empty_course():
    for course_id in EMPTY_COURSE_CANDIDATES:
        try:
            r = requests.get(f"{BASE}/materials/{course_id}", timeout=30)
            if r.status_code == 200 and not r.json().get("materials"):
                return course_id
        except requests.RequestException:
            return None
    return None


EMPTY_COURSE_ID = find_empty_course()


passed = 0
failed = 0


def check(name, ok, detail=""):
    global passed, failed
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"      {detail}")
    if ok:
        passed += 1
    else:
        failed += 1


def post(url, payload):
    body = {"user_id": TEST_USER_ID, "course_id": TEST_COURSE_ID, **payload}
    return requests.post(url, json=body, timeout=300)


print("=" * 50)
print("POST /chat — single agent")
print("=" * 50)

single_agent_tests = [
    ("FAQ, keyword routed", {"message": "What is the grading breakdown?"}, "faq"),
    ("Quiz, keyword routed", {"message": "Generate a quiz on paradoxes"}, "quiz"),
    ("Study, keyword routed", {"message": "Make a study plan for the exam"}, "study"),
    # "final" would send this to study under keyword rules; the explicit
    # agent field must win.
    ("Explicit agent beats keywords",
     {"message": "practice questions for the final", "agent": "quiz", "num_questions": 2},
     "quiz"),
]

for name, payload, expected_agent in single_agent_tests:
    r = post(CHAT_URL, payload)

    if r.status_code == 401:
        check(name, False, "got 401 — set REQUIRE_AUTH=false in orchestrator-work/.env")
        continue

    if r.status_code != 200:
        check(name, False, f"status {r.status_code}: {r.text[:160]}")
        continue

    agent = r.json().get("agent")
    check(name, agent == expected_agent, f"routed to '{agent}'")


print()
print("=" * 50)
print("Error paths")
print("=" * 50)

r = post(CHAT_URL, {"message": "Quiz me", "agent": "quiz", "course_id": "NOPE999"})
check("Unknown course -> 404", r.status_code == 404, r.json().get("message", "")[:110])

if EMPTY_COURSE_ID is None:
    print("SKIP  Course with no material -> 404")
    print(f"      every candidate {EMPTY_COURSE_CANDIDATES} has material now")
else:
    r = post(CHAT_URL, {"message": "Prepare for the final", "agent": "study",
                        "course_id": EMPTY_COURSE_ID})
    check(f"Course with no material ({EMPTY_COURSE_ID}) -> 404",
          r.status_code == 404, r.json().get("message", "")[:110])

r = post(CHAT_URL, {"message": "   ", "agent": "study"})
check("Empty goal -> 400", r.status_code == 400, r.json().get("message", "")[:110])

r = requests.post(CHAT_URL, json={"message": "hi", "user_id": TEST_USER_ID}, timeout=60)
check("Missing course_id -> 422", r.status_code == 422,
      r.json().get("message", "")[:110])


print()
print("=" * 50)
print("POST /ask — multi-agent workspace")
print("=" * 50)

r = post(ASK_URL, {"message": "Help me get ready for the midterm", "num_questions": 2})

if r.status_code != 200:
    check("Broad query -> 200", False, f"status {r.status_code}: {r.text[:160]}")
else:
    body = r.json()
    selected = body.get("selected_agents", [])

    check("Broad query -> 200", True, f"selected: {selected}")
    check("  more than one agent selected", len(selected) > 1, str(selected))
    check("  overview generated", bool(body.get("overview", "").strip()),
          f"{len(body.get('overview',''))} chars")
    check("  every selected agent returned a result",
          set(body.get("agents", {})) == set(selected),
          str(list(body.get("agents", {}))))

r = post(ASK_URL, {"message": "When are office hours?"})
if r.status_code == 200:
    selected = r.json().get("selected_agents", [])
    check("Narrow factual query -> faq only", selected == ["faq"], str(selected))
else:
    check("Narrow factual query -> faq only", False, f"status {r.status_code}")

# One agent failing must not fail the whole request.
if EMPTY_COURSE_ID is None:
    print("SKIP  Partial failure still returns 200")
    print(f"      every candidate {EMPTY_COURSE_CANDIDATES} has material now")
else:
    r = post(ASK_URL, {"message": "Help me prepare", "course_id": EMPTY_COURSE_ID})
    if r.status_code == 200:
        results = r.json().get("agents", {})
        check("Partial failure still returns 200",
              any(not e.get("success") for e in results.values()),
              str({k: e.get("success") for k, e in results.items()}))
    else:
        check("Partial failure still returns 200", False, f"status {r.status_code}")


print()
print("=" * 50)
print(f"{passed} passed, {failed} failed")
print("=" * 50)

raise SystemExit(1 if failed else 0)
