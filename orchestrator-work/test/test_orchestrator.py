import requests

BASE = "http://127.0.0.1:8001"
CHAT_URL = f"{BASE}/chat"
ASK_URL = f"{BASE}/ask"


# This script sends no Authorization header, so it needs REQUIRE_AUTH=false
# in orchestrator-work/.env.
TEST_USER_ID = "test-user"

# Must be a course that has material ingested in Supabase. Upload
# study-agent/sample.txt to HIST301 first. Every agent, the quiz included,
# answers only from uploaded material.
TEST_COURSE_ID = "HIST301"

# A course nobody has uploaded to. Every agent should report that, rather
# than inventing an answer.
EMPTY_COURSE_ID = "NOPE999"


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

r = post(CHAT_URL, {"message": "Quiz me", "agent": "quiz", "course_id": EMPTY_COURSE_ID})
check("Quiz on a course with no material -> 404", r.status_code == 404,
      r.json().get("message", "")[:110])

r = post(CHAT_URL, {"message": "Prepare for the final", "agent": "study",
                    "course_id": EMPTY_COURSE_ID})
check("Study on a course with no material -> 404",
      r.status_code == 404, r.json().get("message", "")[:110])

r = post(CHAT_URL, {"message": "Quiz me", "agent": "quiz", "num_questions": 500})
check("Absurd num_questions -> 422", r.status_code == 422,
      r.json().get("message", "")[:110])

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

    agents = body.get("agents", {})

    study = agents.get("study", {})
    if study.get("success"):
        plan = study["response"]
        check("  study plan is a list of plain-text steps",
              plan["study_plan"] and all(
                  isinstance(x, str) and not x.lstrip().startswith("{")
                  for x in plan["study_plan"]),
              f"{len(plan['study_plan'])} steps")
        check("  study plan cites its sources", bool(plan.get("sources")),
              str(plan.get("sources")))

    quiz = agents.get("quiz", {})
    if quiz.get("success"):
        qs = quiz["response"]["questions"]
        check("  every quiz question has 4 distinct choices and a valid answer",
              qs and all(len(set(q["choices"])) == 4 and q["answer"] in q["choices"]
                         for q in qs),
              f"{len(qs)} questions")

r = post(ASK_URL, {"message": "When are office hours?"})
if r.status_code == 200:
    selected = r.json().get("selected_agents", [])
    check("Narrow factual query -> faq only", selected == ["faq"], str(selected))
else:
    check("Narrow factual query -> faq only", False, f"status {r.status_code}")

# Agents fail independently. A course with nothing uploaded makes every agent
# fail, and the request must still come back as a 200 that says so.
r = post(ASK_URL, {"message": "Help me prepare", "course_id": EMPTY_COURSE_ID})
if r.status_code == 200:
    body = r.json()
    results = body.get("agents", {})
    check("Every agent failing still returns 200",
          bool(results) and all(not e.get("success") for e in results.values()),
          str({k: e.get("success") for k, e in results.items()}))
    check("  overview explains what happened", bool(body.get("overview", "").strip()),
          body.get("overview", "")[:90])
else:
    check("Every agent failing still returns 200", False, f"status {r.status_code}")


print()
print("=" * 50)
print(f"{passed} passed, {failed} failed")
print("=" * 50)

raise SystemExit(1 if failed else 0)
