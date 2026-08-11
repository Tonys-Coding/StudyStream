from pathlib import Path
import os
import shutil
import tempfile

import pypdf
from docx import Document
from dotenv import load_dotenv
from fastapi import UploadFile
from openai import AzureOpenAI
from supabase import create_client


# Formats extract_text_from_file knows how to read.
SUPPORTED_EXTENSIONS = (".txt", ".pdf", ".docx")


# Load root .env first
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)


EMBEDDING_DEPLOYMENT_NAME = os.getenv(
    "AZURE_EMBEDDING_DEPLOYMENT_NAME"
)

DEPLOYMENT_NAME = os.getenv(
    "AZURE_DEPLOYMENT_NAME"
)

print("Embedding deployment:", EMBEDDING_DEPLOYMENT_NAME)
print("Chat deployment:", DEPLOYMENT_NAME)

def get_course_context(course_id: str, goal: str):

    if not goal: 
        raise ValueError("Goal is required to retrieve course context.")

    results= retrieve_relevant_chunks(course_id, goal)
    contents = [r["content"] for r in results]

    return {"content_chunks": contents}
    

def extract_text_from_file(file_path: str) -> str:
    fileName = Path(file_path).suffix

    if fileName == ".txt":
        with open(file_path, 'r') as file:
            return file.read()
        
    elif fileName == ".pdf":

        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    elif fileName == ".docx":
        doc = Document(file_path)
        text =""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    
    else:
        raise ValueError(f"Unsupported file type: {fileName}. Only .txt, .pdf, and .docx are supported.")

   
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits the input text into chunks of specified size with optional overlap.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap  # Move start forward by chunk_size minus overlap

    return chunks


def embed_chunk(text: str) -> list[float]:

    print("Embedding deployment used:", EMBEDDING_DEPLOYMENT_NAME)

    response = client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT_NAME,
        input=text
    )

    return response.data[0].embedding

def save_upload_temporarily(file: UploadFile) -> str:
    """
    Spools an upload to disk so the extractors can read it by path.

    Keeps the original suffix, since extract_text_from_file dispatches on it.
    """

    suffix = Path(file.filename or "").suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        return tmp.name


def ingest_file(
        file_path: str,
        course_id: str,
        tag: str = "document",
        source: str | None = None
) -> int:
    """
    Chunks, embeds, and stores a file. Returns the number of chunks written.

    `source` should be the name the student uploaded. Without it this falls
    back to the path's filename, which for a spooled upload is a temp name
    like "tmp17uzcv0v.txt" - useless for telling materials apart later.
    """

    text = extract_text_from_file(file_path)
    chunks = chunk_text(text)

    if not text.strip():
        raise ValueError("That file appears to be empty - no text could be read from it.")

    source = source or Path(file_path).name

    for chunk in chunks:
        embedding_vector = embed_chunk(chunk)

        supabase.table("course_materials").insert({
            "course_id": course_id,
            "tag": tag,
            "source": source,
            "content": chunk,
            "embedding": embedding_vector
        }).execute()

    return len(chunks)


# The description column is optional, so this keeps working against a
# database where it has not been added yet. See Supabase_Setup.md.
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
        supabase.table("course_materials") \
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


def list_materials(course_id: str) -> list[dict]:
    """
    One entry per uploaded file for this course, with its chunk count.
    """

    columns = "source,tag"

    if has_description_column():
        columns += ",description"

    response = supabase.table("course_materials") \
        .select(columns) \
        .eq("course_id", course_id) \
        .execute()

    # Chunks of the same file share one description; keep the first non-empty.
    grouped: dict[tuple[str, str], dict] = {}

    for row in response.data or []:

        key = (row["source"], row["tag"])
        entry = grouped.setdefault(key, {"chunks": 0, "description": None})

        entry["chunks"] += 1

        if entry["description"] is None and row.get("description"):
            entry["description"] = row["description"]

    return [
        {
            "source": source,
            "tag": tag,
            "chunks": entry["chunks"],
            "description": entry["description"],
        }
        for (source, tag), entry in sorted(grouped.items())
    ]


def list_courses() -> list[dict]:
    """
    Every course that has material ingested, with its chunk count.

    Lets the UI show courses that exist in the database but are not in a
    given browser's local list.
    """

    response = supabase.table("course_materials") \
        .select("course_id") \
        .execute()

    counts: dict[str, int] = {}

    for row in response.data or []:
        counts[row["course_id"]] = counts.get(row["course_id"], 0) + 1

    return [
        {"course_id": course_id, "chunks": n}
        for course_id, n in sorted(counts.items())
    ]


def delete_material(course_id: str, source: str) -> int:
    """
    Removes every chunk of one uploaded file. Returns how many were deleted.
    """

    existing = supabase.table("course_materials") \
        .select("id") \
        .eq("course_id", course_id) \
        .eq("source", source) \
        .execute()

    if not existing.data:
        raise LookupError(
            f"No material named '{source}' found for course {course_id}."
        )

    supabase.table("course_materials") \
        .delete() \
        .eq("course_id", course_id) \
        .eq("source", source) \
        .execute()

    return len(existing.data)


def set_material_description(
        course_id: str,
        source: str,
        description: str
) -> int:
    """
    Sets the description on every chunk of one uploaded file.

    Returns the number of rows updated. Raises if the file is not found.
    """

    if not has_description_column():
        raise RuntimeError(
            "The course_materials table has no 'description' column yet. "
            f"Run this once in the Supabase SQL editor: {ADD_DESCRIPTION_SQL}"
        )

    existing = supabase.table("course_materials") \
        .select("id") \
        .eq("course_id", course_id) \
        .eq("source", source) \
        .execute()

    if not existing.data:
        raise LookupError(
            f"No material named '{source}' found for course {course_id}."
        )

    supabase.table("course_materials") \
        .update({"description": description}) \
        .eq("course_id", course_id) \
        .eq("source", source) \
        .execute()

    return len(existing.data)

def retrieve_relevant_chunks(course_id: str, query: str, match_count: int = 5) -> list[dict]:
    
    query_vector = embed_chunk(query)
    response = supabase.rpc("match_course_materials", {
    "query_embedding": query_vector,
    "match_course_id": course_id,
    "match_count": match_count
}).execute()
    
    return response.data or []
    
def course_has_content(course_id: str) -> bool:
    """
    Cheap existence check to see if this course has any ingested material at all. 
    """

    response = supabase.table("course_materials").select("id").eq("course_id", course_id).limit(1).execute()

    return len(response.data) > 0

