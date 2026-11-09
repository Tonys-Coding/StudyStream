# Backend Integration Notes

This is the write-up of what the backend does now and what had to change to get the React frontend talking to it. The backend started as 3 separate agents that only worked when you called them by hand, so most of this is stuff that broke the first time a browser touched it.

Everything is in `orchestrator-work/`. The frontend is in `classroom-assistant-ui/`.

---

## How a request flows

1. The browser sends the Supabase login token to the orchestrator (:8001).
2. `orchestrator/auth.py` checks the token with Supabase and works out the user id and role from it.
3. For `/ask`, `orchestrator/summarizer.py` picks which agents can help, then the orchestrator calls them in parallel.
4. Each agent pulls the closest chunks of course material (`shared/common.py`), writes its answer, and sends it back.
5. The orchestrator adds a short overview, saves the question and answer to chat history, and returns everything.

The 3 agents (FAQ :8000, Assessment :8002, Study :8003) are only called by the orchestrator. They aren't set up for browser access.

---

## 1. Stuff that stopped the backend from starting

**No `.env` in `orchestrator-work/`.** Every agent loads `orchestrator-work/.env`, so with no file there `AzureOpenAI(api_key=None)` crashed on import. Fix is `cp .env orchestrator-work/.env`. Both `.env` files are gitignored.

**`start.sh` used a venv that didn't exist, and Ctrl+C closed the whole terminal.** It used `trap 'kill 0'`, which signals the whole process group. Now it finds its own folder, takes a `VENV` override, complains if `.env` or the venv is missing, and only stops the processes it started. There's also a `start.sh` at the project root that starts the backend and the frontend together.

**`python-multipart` was missing.** FastAPI needs it for file uploads, and without it the orchestrator and study agent crash on startup. It's in `shared/requirements.txt` now.

---

## 2. Stuff the browser needed

**CORS.** None of the services had it, so every browser request failed at preflight. It's only on the orchestrator (the agents shouldn't be reachable from a browser). Allowed origins come from `FRONTEND_ORIGINS` and default to `http://localhost:5173,http://127.0.0.1:5173`.

**Real authentication.** The orchestrator used to read `user_id` from the request body and trust it. Now `auth.py` verifies the bearer token with Supabase and the user id comes from that. If a token is sent, a `user_id` in the body is ignored.

`REQUIRE_AUTH=false` lets you call the API without a token for local testing (`/docs` and the test script need this). It defaults to **true** and prints a warning at startup when it's off. Never leave it off on a real deployment, since any request could then claim to be any user.

**One error shape.** Agents returned `{"detail": ...}`, network failures were plain 500s, and validation errors were a third format. Now every failure from the orchestrator looks like this:

```json
{ "success": false, "message": "Study Agent: No course material found for CS2336." }
```

Status codes carry through from whichever agent failed (400, 401, 404, 413, 429, 503, 504). The messages are written for the student, so they say "The AI service is busy right now. Try again in a moment." and not a stack trace.

---

## 3. The API right now

| Endpoint | What it does |
| --- | --- |
| `POST /ask` | One question goes to every agent that can help, plus an overview. Also saves the answer to chat history and returns a `session_id` |
| `POST /chat` | One agent only (optional `agent` field skips the keyword routing) |
| `GET /sessions`, `GET /sessions/{id}`, `DELETE /sessions/{id}` | Chat history for a subject |
| `GET /materials/{course_id}` | Files uploaded to a subject |
| `POST /materials/upload` | `.txt`, `.pdf`, `.docx`, capped by `MAX_UPLOAD_MB` (10 by default) |
| `PATCH /materials/{course_id}` | Edit a file's description |
| `DELETE /materials/{course_id}?source=` | Remove a file and all its chunks |
| `GET /me`, `POST /profile/setup` | Who you are and first-time profile creation |
| `GET /courses`, `POST /courses`, `DELETE /courses/{id}` | Your subjects. `POST` takes `public` (teachers only) |
| `POST /activity/quiz` | Saves a finished quiz score |
| `GET /dashboard` | Totals per subject, recent activity, class totals for teachers |
| `GET/POST/PATCH/DELETE /assignments` | The Upcoming Assignments list |
| `GET /teacher/code`, `GET /teacher/roster` | A teacher's code and the people linked to them |
| `GET /teachers`, `POST /teachers/link`, `DELETE /teachers/{id}` | What a student or TA sees: enter a code, list teachers, unlink |

The exact request and response shapes are in [`orchestrator-work/API_CONTRACT.md`](orchestrator-work/API_CONTRACT.md).

### Agents fail on their own

`/ask` always returns 200 and each agent entry is either `{"success": true, "response": ...}` or `{"success": false, "message": ...}`. One subject missing files doesn't sink the whole request. The agent picking is on purpose a little picky: broad "help me prepare" questions go to all 3, but something narrow like "when are office hours?" stays on FAQ only. If the model's pick can't be parsed it falls back to the keyword rules, and the FAQ agent always runs so summaries and "explain it simply" questions get an answer.

### Roles

Students upload files that are private to them. Teachers and TAs upload files shared with the class, and only they can edit or delete class files. Signing up as a teacher or TA needs `TEACHER_INVITE_CODE`. If that isn't set, nobody can claim those roles.

Only teachers can make a subject **public**, and a public subject is only visible to people who entered that teacher's code. The code is 8 characters (shown like `ABCD-2345`) with the look-alike characters left out (no `0`, `O`, `1`, `I`, `L`). Unlinking also removes the person from that teacher's public subjects.

---

## 4. Bugs that showed up while wiring it together

These had nothing to do with the frontend, but they made the app give wrong answers.

- **The study agent made up plans from nothing.** `get_course_context` always returns a dict, so `if not course_context:` was never true and an empty search went straight to the model. A subject with 0 files got a confident generic study plan. It now checks `content_chunks` and returns a 404.
- **Blank goals gave a 500.** The empty check ran after retrieval, which crashes on an empty goal. Moved it before.
- **PDF and DOCX uploads crashed.** `extract_text_from_file` used `pypdf` and `Document` without importing them, so only `.txt` ever worked.
- **Uploads were saved under the temp filename** (stuff like `tmphcdtt92o.txt`) instead of the real name.
- **Every study request embedded the goal twice.** Two Azure calls and two vector searches per request. It's one now.
- **The FAQ agent was a stub** that returned `Received question: ...`. It now does retrieval and only answers from the material, and says so when the material doesn't cover it.
- **Quizzes were hardcoded.** The assessment agent used a fixed list of topics per course. It now builds questions from the retrieved material, checks that each one has 4 different choices and an answer that is one of them, and writes a short explanation for every question (that's what shows up in green or red under each question).
- **The auth helper from the early prototype could never work.** It put the key in the URL's place:

```python
SUPABASE_KEY = os.getenv("SUPABASE_URL")   # wrong name
SUPABASE_KEY = os.getenv("SUPABASE_KEY")   # overwrites it
supabase = create_client(SUPABASE_KEY, SUPABASE_KEY)   # key used as the URL
```

---

## 5. Things that were fixed in the database

- **Row level security was off** on `course_materials` and `profiles`. The `anon` key ships inside the frontend, so anyone could read or write those tables directly. Writing was the bad part, since text someone inserted would be retrieved and given to the model as trusted course material. RLS is now on for every table with no policies (see `DATABASE_SETUP.md` for why).
- **Mislabeled course material.** A syllabus for a different course had been uploaded under the wrong `course_id`, so asking about one course returned the other one's content. Fixed with an `UPDATE`. Embeddings come from the content, so there was no need to re-embed.
- **Junk chunks** from test uploads were deleted. They were making one subject's plans come out as nonsense.
- **New tables** for subjects, enrollments, activity, chat history, assignments and teacher codes (`DATABASE_MIGRATION.sql`).
- **Per-user retrieval.** The search function has a version that takes the requesting user, so class material is shared and private material only shows up for whoever uploaded it.

If a table or column from the migration is missing, the API answers with a message telling you to run it instead of a raw database error.

Still worth doing later: confirm `embedding` has a vector index (`ivfflat` or `hnsw`), because without one a similarity search reads every row.

---

## 6. Tests

- `test/test_units.py` (106 checks) needs no Azure or Supabase. It uses a fake in-memory database to test chunking, JSON parsing, chat history, assignments, teacher codes, public subjects and the role rules. The teacher code test caught one real bug: unlinking a student left them enrolled in that teacher's public subjects.
- `test/test_orchestrator.py` calls the running backend with real Azure calls and takes about 90 seconds. It finds an empty subject at runtime instead of hardcoding one (an earlier version used a fixed course, which broke the moment somebody uploaded a file to it and looked like a code bug). Run it with `REQUIRE_AUTH=false` since it sends no token.
