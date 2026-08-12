# Backend Changes for Frontend Integration

A record of everything that had to change in the backend before the React
frontend could talk to it. Written for the team, so each item says what was
wrong, not just what changed.

The backend lives in `orchestrator-work/` on the `prototype-v2` branch. The
frontend lives in `classroom-assistant-ui/` on the `frontend` branch.

---

## 1. Things that stopped the backend running at all

### No `.env` in `orchestrator-work/`

Every agent resolves credentials with
`BASE_DIR = Path(__file__).resolve().parent.parent`, which lands in
`orchestrator-work/`. No `.env` existed there, so `load_dotenv` silently did
nothing and `AzureOpenAI(api_key=None)` raised at import. **The study and
assessment agents could not start.**

Fix: `cp .env orchestrator-work/.env`. Both files are gitignored.

### `start.sh` pointed at a venv that did not exist

It ran `source venv/bin/activate`; the actual environment is `.venv-1` at the
project root. It also used `trap 'kill 0'`, which signals the whole process
group — **Ctrl+C killed the user's terminal** along with the services.

Now: resolves its own directory so it works from any cwd, takes a `VENV`
override, fails loudly if `.env` or the venv is missing, and tracks child PIDs
so it stops only what it started.

There was also no launcher at the project root, so `./start.sh` from
`Study-Feedback-Agent/` failed with "no such file". Added `start.sh` at the
root that starts the backend **and** the frontend.

### `python-multipart` was missing

FastAPI requires it for `Form` and `UploadFile`. Without it the orchestrator
and study agent crash at startup once upload endpoints exist. Added to
`shared/requirements.txt`.

---

## 2. Things the browser specifically needed

### CORS

Not one service had `CORSMiddleware`. Every browser request would have failed
at preflight. Added to the **orchestrator only** — the three agents are called
server-to-server and should not be reachable from a browser.

Allowed origins come from `FRONTEND_ORIGINS`, defaulting to
`http://localhost:5173,http://127.0.0.1:5173`.

### Authentication

The orchestrator had none. It read `user_id` from the request body and trusted
it, while the frontend already held a Supabase JWT.

Added `orchestrator/auth.py`, which verifies the bearer token with Supabase and
derives `user_id` from it. **A `user_id` in the request body is now ignored
whenever a token is present.**

This was ported from `study-planning-agent-work/auth.py`, which could never
have worked — it did:

```python
SUPABASE_KEY = os.getenv("SUPABASE_URL")   # assigned into the wrong name
SUPABASE_KEY = os.getenv("SUPABASE_KEY")   # immediately overwritten
supabase = create_client(SUPABASE_KEY, SUPABASE_KEY)   # key passed as the URL
```

Also relaxed: a missing `profiles` row yields `role: None` instead of a 404.
The table is empty, so the original would have locked out every user.

`REQUIRE_AUTH=false` allows unauthenticated calls for local development, so
`/docs` and the test script work without minting a token. It defaults to
**true** in code and prints a warning at startup when off.

### A uniform error shape

Agents returned FastAPI's `{"detail": ...}`, transport failures surfaced as
opaque 500s, and validation errors used a third shape. The frontend had three
formats to handle.

Every failure leaving the orchestrator is now:

```json
{ "success": false, "message": "Study Agent: No course material found for CS2336." }
```

Status codes pass through from whichever agent failed: 400 bad input, 401 auth,
404 no material, 413 too large, 429 rate limited, 503 agent down, 504 timeout.

`orchestrator/agents.py` gained a shared `_post()` that unwraps each agent's
`detail` and maps connection and timeout errors to real codes. Previously a 404
from the study agent reached the browser as an unexplained 500.

---

## 3. API changes the frontend depends on

### `POST /chat` — one agent

Added an optional `agent` field that skips keyword routing entirely.

This matters because the keyword chain checks study words before quiz words, so
*"practice quiz for the final"* routed to **study**. With dedicated UI, the
frontend already knows which agent it wants and should not have to phrase its
way around a keyword table. The keyword path still works when `agent` is
omitted.

Agent labels were normalised to slugs (`"study"`, not `"Study Agent"`) so the
frontend can switch on them. `num_questions` is threaded through instead of
being hardcoded to 5.

### `POST /ask` — every relevant agent at once

New. Backs the workspace UI: one question, fanned out to whichever agents help,
plus a generated overview.

- `orchestrator/summarizer.py` picks the agents and writes the overview
- Agents run in parallel via `ThreadPoolExecutor`
- **Agents fail independently.** Each entry is either
  `{"success": true, "response": ...}` or `{"success": false, "message": ...}`,
  and the top-level status stays 200. One course lacking material cannot sink
  the request.
- Falls back to the keyword rules if the model returns something unparseable

Selection is deliberately biased: broad preparation questions fan out to all
three, while a narrow factual question ("when are office hours?") stays on
`faq` alone rather than having a study plan bolted onto it.

### Other endpoints

| Endpoint | Why |
| --- | --- |
| `POST /profile/setup` | The signup flow called it and it did not exist here — signup 404'd |
| `GET /materials/{course_id}` | Lists uploaded files; tells the UI whether a course can answer anything |
| `POST /materials/upload` | `.txt`, `.pdf`, `.docx`, size-capped |
| `DELETE /materials/{course_id}?source=` | Removes a file and every chunk from it |
| `PATCH /materials/{course_id}` | Optional editable description |
| `GET /courses` | Courses that have material, so uploads are never orphaned |

`/profile/setup` takes a JSON body rather than query parameters — full names
contain spaces.

---

## 4. Bugs found while wiring things up

These were pre-existing and unrelated to the frontend, but they made the
integration produce wrong output.

### The study agent invented plans out of nothing

`get_course_context` always returns a dict, so `if not course_context:` was
never true. An empty retrieval went straight to the model.

Live consequences before the fix:

- **CS2336**, with zero material, returned **200 and a confident generic study
  plan**
- **CS3354** returned a plan advising the student to *"review the essentials.json
  file thoroughly to understand all core concepts"* — invented from a
  `.gitignore` that had been uploaded during testing

A student had no way to tell those from real plans. Now checks
`content_chunks` and returns 404. Note `data.py` already had a
`course_has_content()` helper for exactly this — defined, never called.

### Blank goals returned 500 instead of 400

The empty-goal check ran *after* `get_course_context`, which raises
`ValueError` on an empty goal. Moved ahead of retrieval.

### PDF and DOCX upload raised `NameError`

`extract_text_from_file` called `pypdf.PdfReader` and `Document` without
importing either. Only `.txt` would ever have worked.

### Uploads recorded the wrong filename

`ingest_file` used `Path(file_path).name` on the spooled temp file, so material
was stored under names like `tmphcdtt92o.txt`. That is exactly where the junk
rows in the database came from. It now takes the uploaded name.

### Every study request embedded the goal twice

`main.py` fetched the context, then `agent.py` fetched it again — two Azure
embedding calls and two vector searches per request. `study_and_plan_agent` now
receives the context.

### The FAQ agent was a stub

It returned `f"Received question: {question}"`. Replaced with a RAG-backed
agent that answers only from retrieved material and declines when the material
does not cover the question. It takes `course_id` so retrieval can be scoped,
which the orchestrator was not sending.

---

## 5. Database changes

### Mislabelled course material

`sample.txt` is a **HIST 301 time-travel syllabus** but was ingested under
`course_id = "CS3354"`. Asking CS3354 (Software Engineering) for a study plan
returned Einstein and the Grandfather Paradox, while the quiz agent — reading
its hardcoded topics — talked about Requirements Engineering. Same course, two
unrelated subjects.

Relabelled to `HIST301` with `UPDATE` rather than re-ingesting, since
embeddings are content-derived and stayed valid. `HIST301` was added to
`assessment-agent/data.py` so both agents describe the same course.

### Junk rows removed

Six chunks of a duplicated `.gitignore`, uploaded twice while testing the
upload path. They were why CS3354 produced nonsense.

### Optional `description` column

```sql
alter table course_materials add column if not exists description text;
```

Additive and nullable. Without it the materials table still lists every file;
descriptions just cannot be saved, and the API says so rather than failing
silently.

### Row level security

`course_materials` and `profiles` had RLS **disabled**, so the `anon` key —
which ships inside the frontend bundle and is fully public — could read and
write them directly, bypassing the orchestrator. Writable was the serious part:
anyone could insert rows and poison the RAG, since injected text is retrieved
and fed to the model as trusted course material.

```sql
alter table course_materials enable row level security;
alter table profiles enable row level security;
```

No policies are needed. The frontend only ever calls `supabase.auth.*` and
never queries a table, and the backend uses the `service_role` key, which
bypasses RLS.

### Suggested, not yet applied

```sql
create index if not exists course_materials_course_source_idx
  on course_materials (course_id, source);
```

Every material query filters on `course_id`; deletes and updates filter on
`(course_id, source)`. Irrelevant at current size, worth having before a class
uploads real material.

Also worth confirming in the dashboard that `embedding` has a vector index
(`ivfflat` or `hnsw`) — without one, similarity search is a full scan.

---

## 6. Tests

`test/test_orchestrator.py` sent only `{"message": ...}`, so every request was
a guaranteed 422 once `user_id` and `course_id` became required. It also
asserted nothing — it printed responses and always "passed".

Now 14 assertions covering `/ask`, single-agent routing, explicit-agent
override, and the error paths, with a pass/fail count and a non-zero exit code.

It discovers an empty course at runtime rather than hardcoding one. An earlier
version pinned `CS2336`, which broke the moment someone uploaded a file to it —
the failure looked like a code regression but was a stale fixture.

Run with `REQUIRE_AUTH=false` in `orchestrator-work/.env`, since the script
sends no token.
