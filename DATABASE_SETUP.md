# Database Setup

This is how to set up your own Supabase project for StudyStream. It takes about 10 minutes and the free tier is enough.

The app uses Supabase for 3 things: user accounts, course material stored as embeddings (so it can be searched), and everything else the app remembers (subjects, chat history, assignments, teacher codes).

---

## Step 1: Create a Supabase project

1. Sign up at [supabase.com](https://supabase.com).
2. Click **New project**. Any name and region works.
3. Save the database password it makes for you. You won't need it here but it isn't shown again.

Wait for it to finish setting up before moving on.

---

## Step 2: Create the main tables

Open **SQL Editor** in the sidebar, paste all of this, and run it once.

```sql
-- pgvector, for searching by meaning
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

-- Every query filters on course_id, and uploads/deletes also filter on source
create index if not exists course_materials_course_source_idx
  on course_materials (course_id, source);


-- User profiles, tied to Supabase's auth.users
create table if not exists profiles (
  id        uuid primary key references auth.users (id) on delete cascade,
  role      text not null,
  full_name text
);


-- Search for someone who isn't signed in as a real user (local dev only):
-- class material only
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
        id, course_id, tag, content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM course_materials
    WHERE course_id = match_course_id
      AND visibility = 'class'
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$function$;


-- Search for a real user: class material (shared) plus their own private
-- uploads. This is the one the app uses for signed-in users.
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


-- Lock both tables down (see "Why there are no policies" below)
alter table course_materials enable row level security;
alter table profiles enable row level security;
```

> `vector(1536)` matches OpenAI's `text-embedding-3-small`. If you use a different embedding model, change the number to match it or every upload will fail.

### Step 2b: Run the migration

Still in the SQL editor, paste [`DATABASE_MIGRATION.sql`](DATABASE_MIGRATION.sql) and run it once. It adds the tables for the rest of the app:

| Table | What it holds |
| --- | --- |
| `courses` | The list of subjects, each one public or private |
| `enrollments` | Which subjects each person has added |
| `activity` | Questions asked and quiz scores, for the Dashboard |
| `chat_sessions` | Every question and its full answer, so you can reopen it |
| `assignments` | The Upcoming Assignments list |
| `teacher_codes` | Each teacher's personal code |
| `teacher_links` | Which students and TAs entered which teacher's code |

It's safe to run again, it doesn't change or delete anything that's already there, and it adds 3 starter subjects so a new account has something to join.

---

## Step 3: Turn off email confirmation

Go to **Authentication -> Sign In / Providers -> Email** and turn off "Confirm email".

If it's on, signing up gives back a user but no session, so the app has no token to send and creating the profile fails. You can turn it back on for a real deployment.

---

## Step 4: Copy your keys into the project

**Project Settings -> API Keys.** Backend, in `orchestrator-work/.env`:

```text
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_KEY=<service_role key>
```

Frontend, in `classroom-assistant-ui/.env`:

```text
VITE_SUPABASE_URL=https://xxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
VITE_API_BASE_URL=http://127.0.0.1:8001
```

**The two keys are not the same thing:**

| Key | Goes in | Why |
| --- | --- | --- |
| `service_role` | Backend only | Full access, skips RLS. Treat it like a password. |
| `anon` | Frontend | Meant to be public since it ships in the browser code. |

If the `service_role` key ends up in the frontend, anyone who opens dev tools gets full access to your database. Both `.env` files are gitignored, so don't force-add them.

The backend also needs the Azure OpenAI values and `TEACHER_INVITE_CODE` in `orchestrator-work/.env`. `.env.example` lists all of them.

---

## Step 5: Check that it worked

From the project root:

```bash
./start.sh
```

Sign up, add a subject, and upload a `.txt` file. If it shows up in the Course Material table, the whole path works (reading the file, splitting it up, embedding, saving, and searching).

To check from SQL:

```sql
select course_id, source, count(*) as chunks
from course_materials
group by course_id, source;
```

To try the teacher side, sign up a second account as a teacher (use your `TEACHER_INVITE_CODE`), make a **Public** subject, upload a file, and copy the code from the **Your class** page. Then enter it from a student account under **Teachers** and the subject shows up under **Shared**.

---

## Why there are no policies

Row level security (RLS) is on for every table with no policies, which blocks everything by default. That's on purpose and not something I forgot:

- The **backend** uses the `service_role` key, which skips RLS, so the agents aren't affected.
- The **frontend** only calls `supabase.auth.*` and never reads a table directly. Every data request goes through the orchestrator, which checks the login token first.

Without this, the public `anon` key could read and write `course_materials`. Writing is the dangerous part, since anyone could insert text and it would be retrieved and handed to the model as trusted course material.

If you ever want the browser to query tables directly you'll need to write policies first. Until then, leaving it closed is correct.

---

## Table reference

### `course_materials`

One row per chunk, so one uploaded file becomes a lot of rows.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `bigint` | Primary key |
| `course_id` | `text` | Which subject, like `CS3354`. Every query filters on it |
| `tag` | `text` | Category (`syllabus`, `uploaded`, etc.) |
| `source` | `text` | The original filename. Deletes and descriptions use it |
| `content` | `text` | The chunk of text |
| `embedding` | `vector(1536)` | Its embedding |
| `uploaded_by` | `uuid` | Who uploaded it |
| `visibility` | `text` | `class` (shared, uploaded by a teacher or TA) or `private` (a student's own). Defaults to `class` |
| `description` | `text` | Optional note, editable in the Overview tab |

Chunks are about 1000 characters and end at a paragraph or sentence when they can, with 150 characters of overlap so an idea that gets cut still shows up whole in one chunk. Embeddings are sent to Azure 16 chunks at a time.

### `profiles`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` | Matches the Supabase auth user |
| `role` | `text` | `student`, `teacher` or `ta` |
| `full_name` | `text` | |

Created when someone signs up. Someone with no profile row can still sign in, their role is just unknown.

### `courses` (from the migration)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `text` | The subject code, like `CS3354` |
| `name` | `text` | |
| `created_by` | `uuid` | Who made it |
| `visibility` | `text` | `public` (teacher-made, shown under Shared) or `private` |

The other migration tables are described in the table at Step 2b. `teacher_codes` stores 1 code per teacher, and `teacher_links` stores 1 row for each student or TA who entered it.

---

## Troubleshooting

**`relation "course_materials" does not exist`**
Step 2 didn't run. Run it again in the SQL editor.

**`type "vector" does not exist`**
`create extension if not exists vector;` didn't run, or it ran in a different schema. Run it by itself first, then the rest.

**`expected 1536 dimensions, not N`**
Your embedding model doesn't make 1536-number vectors. Use `text-embedding-3-small` or change the column to match.

**`Could not find the function public.match_course_materials`**
The function part didn't run. Run just that part again.

**A page says to run the database migration**
Run `DATABASE_MIGRATION.sql` (Step 2b). The app still starts without it but those pages can't load.

**Uploads work but questions say "No course material found"**
Search is filtered by subject, so make sure you're asking about the same one you uploaded to. A student's uploads are also private, so a different account won't see them.

**Everything returns 401**
For local work set `REQUIRE_AUTH=false` in `orchestrator-work/.env`. It has to be `true` anywhere else, since with it off any request can claim to be any user.
