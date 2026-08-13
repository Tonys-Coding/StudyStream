# StudyStream: An AI Classroom Assistant

A multi-agent study assistant for university courses. A student uploads their
course material — a syllabus, lecture notes, a reading — then asks a question
in plain language. The question goes to every assistant that can help, and each
one's work appears in its own tab alongside a combined summary.

Three specialists sit behind one orchestrator:

| Agent | What it does |
| --- | --- |
| **Study Planning** | A step-by-step plan, focus topics, an estimated time to spend |
| **Assessment** | Multiple-choice practice questions |
| **FAQ** | Direct answers about the course — grading, deadlines, readings, policies |

Study and FAQ answer from the student's own uploaded material using retrieval
over embeddings, so they quote real details instead of inventing them. Both
decline rather than guess when the material does not cover a question.

---

## How it fits together

```text
Browser (React + TypeScript, :5173)
        |  POST /ask   Authorization: Bearer <supabase jwt>
        v
Orchestrator (FastAPI, :8001)      <- the only browser-facing service
        |  picks the relevant agents, calls them in parallel
        +---------------+---------------+
        v               v               v
   FAQ (:8000)   Assessment (:8002)  Study (:8003)
        |               |               |
        +---------------+---------------+
                        v
        Supabase (pgvector) + Azure OpenAI
```

The orchestrator verifies the Supabase JWT once, for everything. The three
agents are called server-to-server and are not exposed to the browser.

Agents fail independently — if a course has no material, the study and FAQ tabs
report that while the quiz tab still works.

See [`API_CONTRACT.md`](orchestrator-work/API_CONTRACT.md) for exact request and
response shapes, and [`BACKEND_INTEGRATION.md`](BACKEND_INTEGRATION.md) for what
changed in the backend to make this work.

---

## Repository layout

**This branch holds the whole working system — frontend and backend together.**
Clone it and you have everything needed to run the project.

Development happens on separate branches, which this branch combines:

| Branch | Contents |
| --- | --- |
| `frontend` | The React app, root launcher, shared docs |
| `prototype-v2` | Orchestrator and all three agents |
| `study-planning-agent` | Standalone study-agent work |
| `final-prototype` | **This branch** — everything merged and working |

On the development branches the backend is a separate clone nested inside the
frontend checkout, so it shows as untracked there. Here it is tracked normally
under `orchestrator-work/`.

When making changes, work on the development branch that owns the code, then
bring it into this one. Editing here directly means the change is missing from
whichever branch a teammate is working on.

```text
Study-Feedback-Agent/
├── start.sh                     <- starts everything
├── .env                         <- backend credentials (gitignored)
├── .env.example
├── README.md
├── BACKEND_INTEGRATION.md
├── DATABASE_SETUP.md            <- set up your own database
├── Supabase_Setup.md            <- team's shared database
│
├── classroom-assistant-ui/      <- React frontend, port 5173
│   ├── .env                     <- frontend config (gitignored)
│   └── src/
│       ├── components/          Layout, panels, materials table
│       ├── lib/                 api client, auth, courses
│       └── pages/               AuthPage, WorkspaceView
│
└── orchestrator-work/           <- the backend
    ├── start.sh                 <- backend only
    ├── .env                     <- copy of the root .env
    ├── orchestrator/            port 8001
    ├── faq-agent/               port 8000
    ├── assessment-agent/        port 8002
    ├── study-agent/             port 8003, also owns uploads
    ├── shared/requirements.txt
    └── test/test_orchestrator.py
```

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 20+
- Access to the team's Azure OpenAI and Supabase projects

### 1. Virtual environment

From the project root:

```bash
python3 -m venv .venv-1
source .venv-1/bin/activate          # Windows: .venv-1\Scripts\activate
pip install -r orchestrator-work/shared/requirements.txt
```

### 2. Frontend dependencies

```bash
cd classroom-assistant-ui && npm install && cd ..
```

### 3. Credentials

Two `.env` files, both gitignored. **Never commit either.**

**Backend** — every agent reads `orchestrator-work/.env`:

```bash
cp .env.example .env
# fill in the Azure and Supabase values
cp .env orchestrator-work/.env
```

Use the Supabase **service_role** key here, not the anon key.

Setting this up on your own? [`DATABASE_SETUP.md`](DATABASE_SETUP.md) walks
through creating your own Supabase project from scratch — you do not need
access to ours. Team members working against the shared database should use
[`Supabase_Setup.md`](Supabase_Setup.md).

**Frontend** — `classroom-assistant-ui/.env`:

```text
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_API_BASE_URL=http://127.0.0.1:8001
```

The frontend uses the **anon** key, because it runs in the browser.

### 4. Database

**Using your own Supabase project?** Follow
[`DATABASE_SETUP.md`](DATABASE_SETUP.md) — it has the complete schema as one
copy-paste block, plus the keys, and takes about ten minutes.

**Using the team's shared project?** It is already set up. If any of these
have not been applied yet, run them once in the SQL editor:

```sql
-- Optional description shown beside each uploaded file
alter table course_materials add column if not exists description text;

-- Required: without this the public anon key can read and write these
-- tables directly, bypassing the orchestrator
alter table course_materials enable row level security;
alter table profiles enable row level security;
```

No RLS policies are needed — the backend uses the `service_role` key, which
bypasses RLS, and the frontend never queries tables directly.

### 5. Supabase auth

Turn **off** email confirmation for local development
(Authentication → Providers → Email). With it on, `signUp` returns a user but
no session, so profile setup has no token to send and signup fails.

---

## Running

```bash
./start.sh
```

Starts all four backend services and the frontend dev server.

- Frontend — <http://localhost:5173>
- API docs — <http://127.0.0.1:8001/docs>

Ctrl+C stops everything.

Backend only: `./orchestrator-work/start.sh`
Frontend only: `cd classroom-assistant-ui && npm run dev`

To use a different virtual environment: `VENV=../.venv ./orchestrator-work/start.sh`

### One service at a time

Each service runs from inside its own folder, because the imports are flat:

```bash
cd orchestrator-work/faq-agent
uvicorn main:app --reload --port 8000
```

Ports: FAQ 8000, Orchestrator 8001, Assessment 8002, Study 8003.

---

## Using it

1. Sign up, then pick a subject in the sidebar.
2. Upload material — the paperclip in the chat bar, or **Upload** in the Course
   Material table. `.txt`, `.pdf`, and `.docx` are supported.
3. Ask a question. It goes to every assistant that can help.
4. **Overview** holds the summary; **Study & Planning**, **FAQ**, and
   **Assessment** hold each assistant's full work. Tabs are dimmed when that
   assistant had nothing to add.

The Course Material table at the bottom of Overview lists every uploaded file
with an editable description, and lets you remove files.

### Adding a course

Use **+** beside SUBJECTS in the sidebar. Your subject list is stored in the
browser and merged with any course the backend reports as having material, so
uploads are never orphaned.

One caveat: **quizzes** additionally need the course in `COURSE_DATA` in
`orchestrator-work/assessment-agent/data.py`, because the assessment agent
still reads hardcoded topics rather than Supabase. Study plans and FAQ work
from uploaded material alone.

---

## Tests

With the backend running and `REQUIRE_AUTH=false` in `orchestrator-work/.env`:

```bash
./.venv-1/bin/python orchestrator-work/test/test_orchestrator.py
```

14 checks covering single-agent routing, the multi-agent `/ask` fan-out, and
the error paths. Takes about 90 seconds — most cases make real Azure calls.

---

## Troubleshooting

**"Could not reach the server at http://127.0.0.1:8001"**
The backend is not running. Use `./start.sh` from the project root — note
`orchestrator-work/start.sh` starts the backend only.

**Services exit immediately with `Address already in use`**
An earlier run is still holding the ports:
`pkill -f "uvicorn main:app"`, then start again.

**Agents fail to start / `api_key must be set`**
`orchestrator-work/.env` is missing. `cp .env orchestrator-work/.env`.

**Everything returns 401**
Set `REQUIRE_AUTH=false` in `orchestrator-work/.env` for local work, or send a
real token.

**"No course material found for course_id: …"**
That course has nothing ingested. Upload a file to it. This is correct
behaviour — the agents refuse to invent a plan from nothing.

**Signup fails after creating the account**
Email confirmation is on, so there is no session yet. Turn it off for local
development, or confirm the email and log in.

**Uploads fail to start the service**
`python-multipart` is missing: `pip install -r orchestrator-work/shared/requirements.txt`.

---

## Current state

Working end to end:

- Supabase auth, verified at the orchestrator
- Multi-agent fan-out with a generated overview
- RAG retrieval over uploaded material for study plans and FAQ
- Course material upload, listing, description, and removal
- User-managed subject list

Not done yet:

- The Assessment agent still uses hardcoded topics rather than RAG
- Per-user material visibility — uploads are course-wide
- Student history, progress tracking, instructor analytics
- The dashboard is a placeholder
