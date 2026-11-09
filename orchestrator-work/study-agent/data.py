import os
import shutil
import sys
import tempfile
from pathlib import Path

import pypdf
from docx import Document
from fastapi import UploadFile

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import (
    STAFF_ROLES,
    build_context,
    chunk_text,
    embed_texts,
    is_uuid,
    retrieve,
    supabase,
)


# Formats extract_text_from_file knows how to read.
SUPPORTED_EXTENSIONS = (".txt", ".pdf", ".docx")

# A file that would need more embedding calls than this is almost certainly
# not course notes. Refusing it up front bounds the Azure spend per upload.
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "1500"))

INSERT_BATCH = 100


# -------------------------
# Who can see and change what
# -------------------------
#
# Every row of course_materials has a visibility:
#   "class"    shared with everyone in the course. Teachers and TAs upload
#              these, and only teachers and TAs may change them.
#   "private"  visible to the uploader alone. Students upload these.

def visibility_for(role: str | None) -> str:
    return "class" if role in STAFF_ROLES else "private"


def can_edit(visibility: str, role: str | None) -> bool:
    """Private rows are always the caller's own (see _visible); class rows are staff-only."""
    return visibility == "private" or role in STAFF_ROLES


def _visible(query, user_id: str | None):
    """Limits a query to the rows this user is allowed to see."""

    if is_uuid(user_id):
        return query.or_(
            "visibility.eq.class,"
            f"and(visibility.eq.private,uploaded_by.eq.{user_id})"
        )

    return query.eq("visibility", "class")


def _owner(query, owner: str | None):
    """Matches rows uploaded by `owner`, or with no recorded uploader."""

    if owner:
        return query.eq("uploaded_by", owner)

    return query.is_("uploaded_by", "null")


def _select_all(make_query, page: int = 1000) -> list[dict]:
    """
    Supabase returns at most 1000 rows per request, so a course with more
    chunks than that would be silently truncated. Page through instead.
    """

    rows: list[dict] = []
    start = 0

    while True:
        batch = make_query().range(start, start + page - 1).execute().data or []
        rows.extend(batch)

        if len(batch) < page:
            return rows

        start += page


# -------------------------
# Reading files
# -------------------------

def extract_text_from_file(file_path: str) -> str:

    suffix = Path(file_path).suffix.lower()

    try:

        if suffix == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        if suffix == ".pdf":
            reader = pypdf.PdfReader(file_path)
            return "\n".join(
                (page.extract_text() or "") for page in reader.pages
            )

        if suffix == ".docx":
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)

    except Exception as e:
        raise ValueError(
            f"Could not read that {suffix[1:].upper()} file. It may be "
            f"damaged or password protected. ({type(e).__name__})"
        )

    raise ValueError(
        f"Unsupported file type: {suffix}. "
        "Only .txt, .pdf, and .docx are supported."
    )


def save_upload_temporarily(file: UploadFile) -> str:
    """
    Spools an upload to disk so the extractors can read it by path.

    Keeps the original suffix, since extract_text_from_file dispatches on it.
    """

    suffix = Path(file.filename or "").suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        return tmp.name


# -------------------------
# Ingesting
# -------------------------

def ingest_file(
        file_path: str,
        course_id: str,
        source: str,
        user_id: str | None,
        role: str | None,
        tag: str = "uploaded"
) -> int:
    """
    Chunks, embeds and stores a file. Returns the number of chunks written.

    Every embedding is computed before anything is written, so a failure at
    the Azure step leaves the database untouched. Uploading a file with the
    same name again replaces the earlier copy instead of adding to it.
    """

    text = extract_text_from_file(file_path)

    if not text.strip():
        raise ValueError(
            "That file appears to be empty - no text could be read from it. "
            "Scanned PDFs need OCR first."
        )

    chunks = chunk_text(text)

    if len(chunks) > MAX_CHUNKS:
        raise ValueError(
            f"That file is too long to index ({len(chunks)} sections, the "
            f"limit is {MAX_CHUNKS}). Split it into smaller files."
        )

    vectors = embed_texts(chunks)

    visibility = visibility_for(role)
    owner = user_id if is_uuid(user_id) else None

    rows = [
        {
            "course_id": course_id,
            "tag": tag,
            "source": source,
            "content": chunk,
            "embedding": vector,
            "uploaded_by": owner,
            "visibility": visibility
        }
        for chunk, vector in zip(chunks, vectors)
    ]

    def remove_existing():
        _owner(
            supabase().table("course_materials").delete()
            .eq("course_id", course_id)
            .eq("source", source)
            .eq("visibility", visibility),
            owner
        ).execute()

    remove_existing()

    try:

        for i in range(0, len(rows), INSERT_BATCH):
            supabase().table("course_materials") \
                .insert(rows[i:i + INSERT_BATCH]) \
                .execute()

    except Exception:
        # Do not leave half a file behind.
        remove_existing()
        raise

    return len(rows)


# -------------------------
# Listing, editing, deleting
# -------------------------

def list_materials(
        course_id: str,
        user_id: str | None,
        role: str | None
) -> list[dict]:
    """
    One entry per file this user can see in the course, with its chunk count,
    whether it is shared or private, and whether they may change it.
    """

    rows = _select_all(
        lambda: _visible(
            supabase().table("course_materials")
            .select("source,tag,description,visibility,uploaded_by")
            .eq("course_id", course_id),
            user_id
        ).order("id")
    )

    grouped: dict[tuple[str, str, str], dict] = {}

    for row in rows:

        key = (row["source"], row["tag"] or "", row["visibility"])

        entry = grouped.setdefault(key, {
            "chunks": 0,
            "description": None,
            "mine": False
        })

        entry["chunks"] += 1

        # Chunks of one file share a description; keep the first non-empty.
        if entry["description"] is None and row.get("description"):
            entry["description"] = row["description"]

        if is_uuid(user_id) and row.get("uploaded_by") == user_id:
            entry["mine"] = True

    return [
        {
            "source": source,
            "tag": tag,
            "chunks": entry["chunks"],
            "description": entry["description"],
            "visibility": visibility,
            "mine": entry["mine"],
            "can_edit": can_edit(visibility, role)
        }
        for (source, tag, visibility), entry in sorted(grouped.items())
    ]


def _editable_rows(
        query,
        course_id: str,
        source: str,
        visibility: str,
        user_id: str | None,
        role: str | None
):
    """Scopes a query to rows the caller may change, or raises PermissionError."""

    if not can_edit(visibility, role):
        raise PermissionError(
            "Only teachers and TAs can change material shared with the class."
        )

    query = query.eq("course_id", course_id) \
        .eq("source", source) \
        .eq("visibility", visibility)

    if visibility == "private":

        if not is_uuid(user_id):
            raise PermissionError("Sign in to change your own material.")

        query = query.eq("uploaded_by", user_id)

    return query


def delete_material(
        course_id: str,
        source: str,
        visibility: str,
        user_id: str | None,
        role: str | None
) -> int:
    """Removes every chunk of one uploaded file. Returns how many."""

    def scope(q):
        return _editable_rows(q, course_id, source, visibility, user_id, role)

    existing = scope(
        supabase().table("course_materials").select("id")
    ).execute()

    if not existing.data:
        raise LookupError(
            f"No material named '{source}' found for course {course_id}."
        )

    scope(supabase().table("course_materials").delete()).execute()

    return len(existing.data)


# The description column is optional, so this keeps working against a
# database where it has not been added yet.
_has_description: bool | None = None


def has_description_column() -> bool:
    """
    Only a positive result is cached. Caching a negative would strand a
    running server on 501 after someone adds the column, until a restart.
    """

    global _has_description

    if _has_description:
        return True

    try:
        supabase().table("course_materials") \
            .select("description") \
            .limit(1) \
            .execute()
        _has_description = True
    except Exception:
        return False

    return True


ADD_DESCRIPTION_SQL = (
    "alter table course_materials add column if not exists description text;"
)


def set_material_description(
        course_id: str,
        source: str,
        description: str,
        visibility: str,
        user_id: str | None,
        role: str | None
) -> int:
    """Sets the description on every chunk of one file. Returns rows updated."""

    if not has_description_column():
        print(f"[STUDY AGENT] Add the description column: {ADD_DESCRIPTION_SQL}")

        raise RuntimeError("Descriptions aren't available yet. Please try again later.")

    def scope(q):
        return _editable_rows(q, course_id, source, visibility, user_id, role)

    existing = scope(
        supabase().table("course_materials").select("id")
    ).execute()

    if not existing.data:
        raise LookupError(
            f"No material named '{source}' found for course {course_id}."
        )

    scope(
        supabase().table("course_materials").update({"description": description})
    ).execute()

    return len(existing.data)


# -------------------------
# Retrieval
# -------------------------

def get_course_context(course_id: str, user_id: str | None, goal: str) -> dict:
    """
    The course material most relevant to the student's goal, limited to what
    they are allowed to see.

    Callers must check content_chunks: an empty list means nothing visible is
    ingested for this course, and answering anyway would be invention.
    """

    if not goal:
        raise ValueError("Goal is required to retrieve course context.")

    return build_context(retrieve(course_id, user_id, goal, k=8))
