# AI Classroom Assistant API Contract

## Version

2.0 — describes the endpoints as implemented.

## Purpose

Defines the interfaces between the frontend, the orchestrator, and the
specialized agents.

---

# System Architecture

```text
Frontend (React + TypeScript, :5173)
        ↓  Authorization: Bearer <supabase jwt>
Orchestrator (FastAPI, :8001)      <- the only browser-facing service
        ↓
FAQ (:8000) | Assessment (:8002) | Study (:8003)
        ↓
Supabase pgvector + Azure OpenAI
```

Only the orchestrator has CORS configured. The agents are called
server-to-server and should not be exposed to the browser.

---

# Authentication

Every orchestrator endpoint except `/health` expects:

```text
Authorization: Bearer <supabase access_token>
```

The orchestrator verifies the token with Supabase and derives `user_id` from
it. **A `user_id` in the request body is ignored whenever a token is
present** — it exists only as a fallback for local development.

Setting `REQUIRE_AUTH=false` in `orchestrator-work/.env` lets unauthenticated
requests through, so `/docs` and the test script work without a token. It must
be `true` anywhere other than a local machine.

---

# Error Format

Every failure from the orchestrator has the same shape:

```json
{
  "success": false,
  "message": "Study Agent: No course material found for course_id: CS2336."
}
```

Status codes are passed through from the agent that failed: 400 bad input,
401 auth, 404 no material, 413 file too large, 429 rate limited, 503 agent
unreachable, 504 timeout.

---

# Orchestrator API

## POST /ask

The workspace endpoint. Sends one message to every relevant agent and returns
all of their output plus a combined overview.

### Request

```json
{
  "message": "Help me get ready for the midterm",
  "course_id": "HIST301",
  "num_questions": 5,
  "agents": ["study", "quiz", "faq"]
}
```

| Field         | Type     | Required | Description                                        |
| ------------- | -------- | -------- | -------------------------------------------------- |
| message       | string   | yes      | The student's question                             |
| course_id     | string   | yes      | Course identifier                                  |
| num_questions | int      | no       | Quiz length, default 5                             |
| agents        | string[] | no       | Forces which agents run. Omit to let the model pick |

### Response

```json
{
  "success": true,
  "query": "Help me get ready for the midterm",
  "overview": "You have a six-step study plan covering...",
  "selected_agents": ["study", "quiz", "faq"],
  "agents": {
    "study": { "success": true, "response": { } },
    "quiz":  { "success": true, "response": { } },
    "faq":   { "success": false, "message": "No course material found." }
  }
}
```

**Agents fail independently.** An entry in `agents` is either
`{"success": true, "response": ...}` or `{"success": false, "message": ...}`.
One agent failing does not fail the request — the top-level status stays 200.

Agent slugs are `study`, `quiz`, and `faq`.

---

## POST /chat

Routes a message to a **single** agent.

### Request

```json
{
  "message": "Generate a quiz on Chapter 4",
  "course_id": "CS3354",
  "agent": "quiz",
  "num_questions": 5
}
```

`agent` is optional. Without it the orchestrator falls back to keyword
matching, where study keywords are checked before quiz keywords — so
"practice quiz for the final" routes to **study**. Pass `agent` explicitly
when you know which one you want.

### Response

```json
{
  "success": true,
  "agent": "quiz",
  "response": { }
}
```

---

## GET /materials/{course_id}

```json
{
  "success": true,
  "course_id": "HIST301",
  "materials": [
    { "source": "syllabus.pdf", "tag": "uploaded", "chunks": 12 }
  ]
}
```

An empty `materials` array means study plans and FAQ answers are not possible
for that course yet.

---

## POST /materials/upload

`multipart/form-data`.

| Field     | Type   | Description                          |
| --------- | ------ | ------------------------------------ |
| course_id | string | Course to attach the material to     |
| file      | file   | `.txt`, `.pdf`, or `.docx` only      |

Rejects unsupported extensions with 400 and files over `MAX_UPLOAD_MB`
(default 10) with 413.

```json
{
  "success": true,
  "source": "syllabus.pdf",
  "course_id": "HIST301",
  "chunks": 12
}
```

---

## POST /profile/setup

```json
{ "role": "student", "full_name": "Jane Doe" }
```

`role` must be `teacher`, `student`, or `ta`. Returns 409 if the profile
already exists.

---

## GET /health

```json
{ "status": "healthy", "service": "orchestrator" }
```

---

# Agent APIs

Called by the orchestrator, not the browser.

## FAQ Agent — POST :8000/faq

```json
{ "question": "What is the grading breakdown?", "course_id": "HIST301" }
```

```json
{ "success": true, "answer": "Paradox Presentations are 20%..." }
```

Answers only from retrieved course material, and says so when the material
does not cover the question. Returns 404 when the course has none.

## Assessment Agent — POST :8002/generate_quiz

```json
{ "user_id": "...", "course_id": "CS3354", "topic": "Testing", "num_questions": 5 }
```

```json
{
  "success": true,
  "questions": [
    { "question": "...", "choices": ["A", "B", "C", "D"], "answer": "B" }
  ]
}
```

Reads `COURSE_DATA` in `assessment-agent/data.py`, **not** Supabase. A course
must be listed there or this returns 404.

## Study Agent — POST :8003/study_plan

```json
{ "user_id": "...", "course_id": "HIST301", "goal": "Prepare for the midterm" }
```

```json
{
  "success": true,
  "study_plan": ["Review weeks 1-4...", "..."],
  "focus_topics": ["Time Dilation"],
  "estimated_hours": 10.0
}
```

`focus_topics` and `estimated_hours` are nullable. Returns 404 when the
course has no ingested material, 400 when `goal` is empty.

The study agent also owns `GET /materials/{course_id}` and
`POST /materials/upload`, which the orchestrator proxies.

---

# Future Enhancements

* RAG for the Assessment agent, replacing its hardcoded topics
* Student progress tracking and instructor analytics
* Per-user material visibility

These should not require changes to the shapes above.
