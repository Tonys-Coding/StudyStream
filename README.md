# AI Classroom Assistant — Backend

The orchestrator and all three specialist agents. The React frontend lives in
the `frontend` branch, under `classroom-assistant-ui/`.

For the project overview and full setup, see the README at the project root.
For exact request and response shapes, see [API_CONTRACT.md](API_CONTRACT.md).
For local setup specifics, see [setup.md](setup.md).

---

## Services

| Service | Port | Role |
| --- | --- | --- |
| **Orchestrator** | 8001 | The only browser-facing service. Verifies the Supabase JWT, decides which agents to call, runs them in parallel, and summarises the result. |
| **FAQ Agent** | 8000 | Answers course questions from retrieved material. |
| **Assessment Agent** | 8002 | Generates multiple-choice practice questions. |
| **Study Agent** | 8003 | Builds study plans. Also owns course material upload and retrieval. |

Only the orchestrator has CORS configured — the agents are called
server-to-server and should not be exposed to a browser.

---

## Running

```bash
./start.sh
```

Starts all four with reload enabled. Requires:

- a virtual environment at `../.venv-1` (override with `VENV=path ./start.sh`)
- a `.env` in this folder — `cp ../.env .env`

API docs at <http://127.0.0.1:8001/docs>.

To start everything including the frontend, use `../start.sh` instead.

### One service at a time

Each runs from inside its own folder, because the imports are flat:

```bash
cd faq-agent
uvicorn main:app --reload --port 8000
```

---

## Where the knowledge comes from

The agents do **not** share one source of truth, which matters when adding a
course:

- **Study and FAQ** retrieve from the `course_materials` table in Supabase,
  filled by uploading files. They return 404 when a course has nothing
  ingested, rather than inventing an answer.
- **Assessment** reads hardcoded topics from `assessment-agent/data.py`. A
  course must be listed there or quiz generation returns 404.

Replacing that hardcoded data with RAG is the main outstanding piece of work.

---

## Layout

```text
orchestrator/
  main.py         endpoints, CORS, error envelope
  auth.py         Supabase JWT verification
  router.py       agent selection, parallel fan-out
  agents.py       HTTP calls to the agents, error passthrough
  summarizer.py   picks the agents, writes the overview

faq-agent/        main, agent, prompts, models, data (retrieval only)
assessment-agent/ main, agent, prompts, models, data (hardcoded topics)
study-agent/      main, agent, prompts, models, data (retrieval + ingestion)

shared/requirements.txt
test/test_orchestrator.py
```

Each agent folder is self-contained: `main.py` holds the endpoints, `agent.py`
the Azure call, `prompts.py` the system prompt, `data.py` the knowledge source.

---

## Tests

With the services running and `REQUIRE_AUTH=false` in `.env`:

```bash
python test/test_orchestrator.py
```

14 checks over single-agent routing, the `/ask` fan-out, and the error paths.
Exits non-zero on failure. The script sends no token, which is why it needs
that flag.

---

## Environment

Read from `.env` in this folder:

| Variable | Purpose |
| --- | --- |
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` | Azure OpenAI |
| `AZURE_DEPLOYMENT_NAME` | Chat model deployment |
| `AZURE_EMBEDDING_DEPLOYMENT_NAME` | Embedding deployment |
| `SUPABASE_URL`, `SUPABASE_KEY` | Supabase, **service_role** key |
| `REQUIRE_AUTH` | `false` relaxes auth for local dev. Defaults to true. |
| `FRONTEND_ORIGINS` | Comma-separated CORS origins |
| `MAX_UPLOAD_MB` | Upload size cap, default 10 |
