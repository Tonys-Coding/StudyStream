# AI Classroom Assistant

## Development Environment Setup

### Prerequisites

* Python 3.10+
* Node.js 20+ (for the frontend)

---

# 1. Create the Virtual Environment

From the **project root** (`Study-Feedback-Agent/`):

```bash
python3 -m venv .venv-1
```

Activate it:

Mac/Linux:

```bash
source .venv-1/bin/activate
```

Windows:

```bash
.venv-1\Scripts\activate
```

---

# 2. Install Dependencies

Backend:

```bash
pip install -r orchestrator-work/shared/requirements.txt
```

Frontend:

```bash
cd classroom-assistant-ui
npm install
```

---

# 3. Configure Credentials

Two `.env` files are needed. Both are gitignored — never commit them.

**Backend** — copy the template and fill it in, then place a copy where the
agents look for it:

```bash
cp .env.example .env
# fill in the Azure and Supabase values
cp .env orchestrator-work/.env
```

Every agent loads `orchestrator-work/.env`. Without it, the study,
assessment, and FAQ agents will not start.

Use the Supabase **service_role** key here, not the anon key. See
`Supabase_Setup.md`.

**Frontend** — `classroom-assistant-ui/.env`:

```text
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_API_BASE_URL=http://127.0.0.1:8001
```

The frontend uses the **anon** key, since it runs in the browser.

---

# 4. Project Structure

```text
Study-Feedback-Agent/
│
├── start.sh                  <- starts everything
├── .env                      <- backend credentials (gitignored)
├── .env.example
│
├── orchestrator-work/
│   ├── start.sh              <- backend only
│   ├── .env                  <- copy of the root .env
│   ├── orchestrator/         <- port 8001, the only browser-facing service
│   ├── faq-agent/            <- port 8000
│   ├── assessment-agent/     <- port 8002
│   ├── study-agent/          <- port 8003, also owns material uploads
│   ├── shared/requirements.txt
│   └── test/test_orchestrator.py
│
└── classroom-assistant-ui/   <- port 5173
```

---

# 5. Running

## Everything at once

From the project root:

```bash
./start.sh
```

That starts the four backend services **and** the frontend dev server.

* Frontend — [http://localhost:5173](http://localhost:5173)
* API docs — [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

CTRL+C stops all of them.

## Backend only

```bash
./orchestrator-work/start.sh
```

Point it at a different virtual environment with `VENV=../.venv ./orchestrator-work/start.sh`.

## Frontend only

```bash
cd classroom-assistant-ui && npm run dev
```

## One service at a time

Each service is run from inside its own folder, because the imports are flat:

```bash
cd orchestrator-work/faq-agent
uvicorn main:app --reload --port 8000
```

Ports: FAQ 8000, Orchestrator 8001, Assessment 8002, Study 8003.

---

# 6. Running Tests

With the backend running, and `REQUIRE_AUTH=false` in `orchestrator-work/.env`:

```bash
python orchestrator-work/test/test_orchestrator.py
```

The script sends no token, so it needs that flag. It prints a pass/fail count.

---

# 7. Adding a Course

A course needs to exist in **both** places, or half the app will 404 for it:

1. **Material for study plans and FAQ** — upload a `.txt`, `.pdf`, or `.docx`
   through the UI (paperclip in the chat bar, or the sidebar's Material
   section). This embeds it into the Supabase `course_materials` table.
2. **Topics for quizzes** — add an entry to `COURSE_DATA` in
   `assessment-agent/data.py`. The assessment agent does not read Supabase.
3. **The picker** — add it to `COURSES` in
   `classroom-assistant-ui/src/lib/courses.ts`.

---

# Current Scope

Working end to end:

* Orchestrator with Supabase JWT auth and CORS
* FAQ, Assessment, and Study Planning agents
* Multi-agent fan-out with a generated overview (`POST /ask`)
* RAG retrieval over uploaded course material
* Course material upload (`.txt`, `.pdf`, `.docx`)
* React frontend with Supabase auth

Not done yet:

* Student history and progress tracking
* Instructor analytics
* The Assessment agent still uses hardcoded topics rather than RAG
* Per-user material visibility (uploads are course-wide)

---

# Expected System Flow

```text
Browser (React, port 5173)
 ↓  POST /ask with a Supabase JWT
Orchestrator (8001) — verifies the token, picks the relevant agents
 ↓  in parallel
FAQ (8000) | Assessment (8002) | Study (8003)
 ↓
Supabase pgvector / hardcoded course data → Azure OpenAI
 ↓
Combined response + overview
```

See `API_CONTRACT.md` for exact request and response shapes.
