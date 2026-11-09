-- StudyStream migration 2: server-side courses, enrollments and activity.
--
-- Run this ONCE in the Supabase SQL editor, after the schema in
-- DATABASE_SETUP.md. It is safe to run again: every statement is idempotent.
--
-- What it adds
--   courses      the catalogue of subjects, public (shared with all students)
--                or private (joined by code)
--   enrollments  which subjects each student has added
--   activity     questions asked and quiz scores, for the Dashboard
--   chat_sessions  every question and its full answer, so you can reopen it
--   assignments    the Upcoming Assignments list on the Dashboard
--   teacher_codes  each teacher's personal code
--   teacher_links  which students/TAs have entered which teacher's code
--
-- Nothing existing is changed or dropped.


create table if not exists courses (
  id         text primary key,
  name       text not null,
  created_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now()
);

-- 'public' subjects are made by a teacher or TA and appear for every student
-- under "Shared" in the sidebar. 'private' ones are joined by course code.
alter table courses
  add column if not exists visibility text not null default 'private'
  check (visibility in ('public', 'private'));


-- Some projects already have an enrollments table, keyed by student_id and
-- linked to profiles. This matches that shape, so on such a database the
-- statement below is skipped and the block after it adds what is missing.
create table if not exists enrollments (
  id         bigint generated always as identity primary key,
  student_id uuid not null references profiles (id) on delete cascade,
  course_id  text not null references courses (id) on delete cascade
);

-- Hardening for an enrollments table that was created without these. The app
-- works without them (it checks for duplicates itself), but the database
-- should refuse them too.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'enrollments_student_course_key'
  ) then
    alter table enrollments
      add constraint enrollments_student_course_key unique (student_id, course_id);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'enrollments_course_id_fkey'
  ) then
    alter table enrollments
      add constraint enrollments_course_id_fkey
      foreign key (course_id) references courses (id) on delete cascade;
  end if;
end $$;


create table if not exists activity (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users (id) on delete cascade,
  course_id  text not null,
  kind       text not null check (kind in ('ask', 'quiz')),
  message    text,
  score      integer,
  total      integer,
  created_at timestamptz not null default now()
);

create index if not exists activity_user_idx
  on activity (user_id, created_at desc);

create index if not exists activity_course_idx
  on activity (course_id, created_at desc);

create index if not exists enrollments_course_idx
  on enrollments (course_id);



create table if not exists chat_sessions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  course_id  text not null,
  title      text not null,
  result     jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists chat_sessions_user_idx
  on chat_sessions (user_id, course_id, created_at desc);


create table if not exists assignments (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users (id) on delete cascade,
  course_id  text,
  title      text not null,
  due_date   date,
  done       boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists assignments_user_idx
  on assignments (user_id, done, due_date);


-- A teacher's personal code. A student or TA who enters it sees that
-- teacher's public subjects under "Shared".
create table if not exists teacher_codes (
  teacher_id uuid primary key references auth.users (id) on delete cascade,
  code       text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists teacher_links (
  student_id uuid not null references auth.users (id) on delete cascade,
  teacher_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (student_id, teacher_id)
);

create index if not exists teacher_links_teacher_idx
  on teacher_links (teacher_id);


-- Same stance as the other tables: no policies, so the public anon key can
-- read nothing. Only the backend (service_role) touches these.
alter table courses     enable row level security;
alter table enrollments enable row level security;
alter table activity    enable row level security;
alter table chat_sessions enable row level security;
alter table assignments   enable row level security;
alter table teacher_codes enable row level security;
alter table teacher_links enable row level security;


-- Starter subjects, so a new user has something to join.
insert into courses (id, name) values
  ('HIST301', 'Time Travel & Historical Paradoxes'),
  ('CS3354',  'Software Engineering'),
  ('CS2336',  'Computer Science II')
on conflict (id) do nothing;
