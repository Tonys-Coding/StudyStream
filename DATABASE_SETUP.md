# Database Setup

**For anyone running this project on their own.** You do not need access to
our team's database — you will create your own in about ten minutes, entirely
on the free tier.

(Team members contributing to the shared course knowledge base should use
`Supabase_Setup.md` instead, which covers the shared project.)

The app needs Supabase for three things: storing course material as
embeddings for retrieval, user accounts, and user profiles.

---

## Step 1 — Create a Supabase project

1. Sign up at [supabase.com](https://supabase.com) — the free tier is enough.
2. **New project.** Pick any name and region.
3. Save the database password it generates. You will not need it for this
   project, but it is not shown again.

Wait for the project to finish provisioning before continuing.

---

## Step 2 — Create the schema

Open **SQL Editor** in the sidebar, paste all of this, and run it once.

```sql
-- pgvector, for similarity search over embeddings
create extension if not exists vector;


-- Course material, one row per chunk of an uploaded file
create table if not exists course_materials (
  id          bigint generated always as identity primary key,
  course_id   text not null,
  tag         text,
  source      text,
  content     text not null,
  embedding   vector(1536),
  uploaded_by uuid,
  visibility  text not null default 'class',
  description text
);

-- Every query filters on course_id; uploads and deletes also filter on source
create index if not exists course_materials_course_source_idx
  on course_materials (course_id, source);


-- User profiles, keyed to Supabase's auth.users
create table if not exists profiles (
  id        uuid primary key references auth.users (id) on delete cascade,
  role      text not null,
  full_name text
);


-- Similarity search. This is the version the app calls today.
create or replace function public.match_course_materials(
  query_embedding vector,
  match_course_id text,
  match_count     integer default 5
)
returns table (
  id         bigint,
  course_id  text,
  tag        text,
  content    text,
  similarity double precision
)
language sql
stable
as $function$
    SELECT
        id,
        course_id,
        tag,
        content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM course_materials
    WHERE course_id = match_course_id
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$function$;


-- Visibility-aware overload: class material is shared, private material is
-- only visible to whoever uploaded it. Not called by the current backend,
-- but the study-planning-agent branch uses it. Safe to include either way.
create or replace function public.match_course_materials(
  query_embedding    vector,
  match_course_id    text,
  requesting_user_id uuid,
  match_count        integer default 5
)
returns table (
  id         bigint,
  course_id  text,
  tag        text,
  content    text,
  similarity double precision
)
language sql
stable
as $function$
    SELECT
        id, course_id, tag, content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM course_materials
    WHERE course_id = match_course_id
      AND (
          visibility = 'class'
          OR (visibility = 'private' AND uploaded_by = requesting_user_id)
      )
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$function$;


-- Lock both tables down. See "Why no policies" below.
alter table course_materials enable row level security;
alter table profiles enable row level security;
```

> `vector(1536)` matches OpenAI's `text-embedding-3-small`. If you use a
> different embedding model, change this number to that model's dimension or
> every insert will fail.

---

## Step 3 — Turn off email confirmation

**Authentication → Sign In / Providers → Email**, and disable "Confirm email".

With it on, signing up returns a user but no session, so the app has no token
to send and profile creation fails. You can turn it back on for a real
deployment.

---

## Step 4 — Copy your keys into the project

**Project Settings → API Keys.** You need three values.

Backend — `orchestrator-work/.env`:

```text
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_KEY=<service_role key>
```

Frontend — `classroom-assistant-ui/.env`:

```text
VITE_SUPABASE_URL=https://xxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
VITE_API_BASE_URL=http://127.0.0.1:8001
```

**The two keys are not interchangeable.**

| Key | Goes where | Why |
| --- | --- | --- |
| `service_role` | Backend only | Full access, bypasses RLS. Treat it like a database password. |
| `anon` | Frontend | Public by design — it ships inside the browser bundle. |

Putting the `service_role` key in the frontend would publish full database
access to anyone who opens dev tools. Both `.env` files are gitignored.

You also need Azure OpenAI credentials in `orchestrator-work/.env` — see
`.env.example` and the main README.

---

## Step 5 — Check it worked

Start the app from the project root:

```bash
./start.sh
```

Then sign up, add a subject, and upload a `.txt` file. If it appears in the
Course Material table with a section count, the whole path works: extraction,
chunking, embedding, storage, and retrieval.

To check from SQL instead:

```sql
select course_id, source, count(*) as chunks
from course_materials
group by course_id, source;
```

---

## Why there are no RLS policies

Row level security is enabled on both tables with **no policies**, which
blocks everything by default. That is deliberate, not unfinished:

- The **backend** uses the `service_role` key, which bypasses RLS entirely,
  so the agents are unaffected.
- The **frontend** only ever calls `supabase.auth.*`. It never queries a
  table — every data request goes through the orchestrator, which verifies
  the user's token first.

Without this, the public `anon` key could read and write `course_materials`
directly. Writing is the dangerous part: anyone could insert rows, and
injected text would be retrieved and handed to the model as trusted course
material.

If you later want the browser to query tables directly, you will need to add
policies. Until then, leaving it closed is correct.

---

## Schema reference

### `course_materials`

One row per chunk. A single uploaded file becomes several rows.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `bigint` | Primary key |
| `course_id` | `text` | Which course, e.g. `HIST301`. Every query filters on this. |
| `tag` | `text` | Category, e.g. `syllabus`, `uploaded` |
| `source` | `text` | Original filename. Deletes and descriptions key off this. |
| `content` | `text` | The chunk of text |
| `embedding` | `vector(1536)` | Its embedding |
| `uploaded_by` | `uuid` | Who uploaded it |
| `visibility` | `text` | `class` or `private`. Defaults to `class`. |
| `description` | `text` | Optional note, editable in the Overview tab |

Chunks are 500 characters with 50 characters of overlap, so a sentence split
across a boundary still appears whole in one of them.

### `profiles`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | Matches the Supabase auth user |
| `role` | `text` | `student`, `teacher`, or `ta` |
| `full_name` | `text` | |

Created when a user signs up. A user without a profile row can still sign in —
their role is simply unknown.

---

## Troubleshooting

**`relation "course_materials" does not exist`**
Step 2 did not run. Re-run it in the SQL editor.

**`type "vector" does not exist`**
`create extension if not exists vector;` did not run, or ran in a different
schema. Run it on its own first, then the rest.

**`expected 1536 dimensions, not N`**
Your embedding model does not produce 1536-dimension vectors. Either switch to
`text-embedding-3-small` or change the column to match your model.

**`Could not find the function public.match_course_materials`**
The function block did not run. Re-run just that part.

**Uploads succeed but questions return "No course material found"**
Retrieval is filtered by `course_id`. Make sure you are asking about the same
subject you uploaded to.

**Everything returns 401**
For local development set `REQUIRE_AUTH=false` in `orchestrator-work/.env`.
It must be `true` anywhere else — with it off, any request can claim any user.
