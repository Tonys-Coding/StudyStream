# Supabase Setup Guide — AI Classroom Assistant

This guide explains how to connect to the project's shared Supabase database (used for RAG — storing course materials as embeddings for retrieval).

## Step 1: Get Access to the Shared Project

To get access:

1. Add your email as a collaborator on the Supabase project (Project Settings → Team → Invite)
2. Once added, log in at [supabase.com](https://supabase.com) and you'll see the project in your dashboard

**Do not create your own separate Supabase project** unless the team explicitly decides to split databases per agent — 
we're using one shared database so all agents can eventually read from the same course knowledge base.

---

## Step 2: Get Your Environment Variables

Once you have access to the project:

1. Go to **Project Settings** (gear icon) → **API Keys**
2. You'll need two values:
   - **Project URL** — Find the Project ID in General Settings, then: https://xxxxx.supabase.co
   - **service_role key** — long string, full database access, treat like a password

Add these to your local `.env` file (never commit this file — it should already be in `.gitignore`):
- SUPABASE_URL=https://xxxxx.supabase.co
- SUPABASE_KEY=your_service_role_key_here

**Important:** use the `service_role` key for backend code (like our agents), not the `anon` key — the `anon` key is 
meant for client-side/public-facing use and has restricted permissions by design.

## Step 3: Install the Python Client

```bash
pip install supabase
```

(This should already be listed in the shared `requirements.txt` on `main` 

---

## Step 4: Connect From Your Code
```python

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

script_dir = Path(__file__).parent
load_dotenv(script_dir / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
```

This gives you a `supabase` client object you can use to query or insert data.

---

## Step 5: Understand the Current Schema

There is currently one table, `course_materials`, used for storing course content as embeddings:

| Column | Type | Description |
|---|---|---|
| `id` | `bigint` | Auto-incrementing row ID |
| `course_id` | `text` | Which course this chunk belongs to (e.g., `"CS3354"`) |
| `tag` | `text` | Category label (e.g., `"syllabus"`, `"lecture_notes"`) |
| `source` | `text` | Filename the chunk came from |
| `content` | `text` | The actual chunk of text |
| `embedding` | `vector(1536)` | The embedding vector (from `text-embedding-3-small`) |

There's also a Postgres function, `match_course_materials`, used to run similarity search — given a query embedding and a `course_id`, it returns the closest-matching chunks for that course.

### Optional: `description` column

The Overview tab shows a table of uploaded material with a short, editable
description per file. That needs one extra column. Run this once in the
Supabase SQL editor:

```sql
alter table course_materials add column if not exists description text;
```

It is additive and nullable, so it cannot break existing queries. Until it is
added, the materials table still lists every file — descriptions just cannot
be saved, and the app says so rather than failing silently.

**If your agent needs a new table or new columns, please coordinate first** — since this is a shared database, 
uncoordinated schema changes could break other agents' queries.

---

## Step 6: Basic Usage Examples

**Querying existing data:**
```python
response = supabase.table("course_materials") \
    .select("*") \
    .eq("course_id", "CS3354") \
    .execute()

print(response.data)
```

**Checking if a course has any content (cheap check, no similarity search):**
```python
response = supabase.table("course_materials") \
    .select("id") \
    .eq("course_id", "CS3354") \
    .limit(1) \
    .execute()

has_content = len(response.data) > 0
```

**Running a similarity search (requires an embedding vector — see the RAG pipeline docs on Anthony's wiki page for how embeddings are generated):**
```python
response = supabase.rpc("match_course_materials", {
    "query_embedding": your_query_vector,   # a list of 1536 floats
    "match_course_id": "CS3354",
    "match_count": 5
}).execute()

print(response.data)
```
