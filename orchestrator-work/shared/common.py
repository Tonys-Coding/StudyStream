"""
Code every service needs, in one place.

Each service runs from its own folder, so they reach this module by adding
this folder to sys.path:

    sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))
    from common import ...

It owns the Azure and Supabase clients, JSON handling for model output,
batched embeddings, chunking, and retrieval.
"""

import json
import os
import re
import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI, BadRequestError
from supabase import create_client


# Every service loads the same orchestrator-work/.env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

CHAT_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT_NAME")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME")

# Roles that may share material with a whole class.
STAFF_ROLES = ("teacher", "ta")


class ModelOutputError(Exception):
    """The model answered, but not in a shape we can use."""


# -------------------------
# Clients
# -------------------------

_azure = None

# FastAPI runs these endpoints on a thread pool. A Supabase client shares one
# HTTP/2 connection, and using it from several threads at once fails with
# "ReadError: Resource temporarily unavailable", which a page that fires
# several requests together (the dashboard does) hits. One client per thread.
_local = threading.local()


def azure():
    global _azure

    if _azure is None:
        _azure = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=AZURE_API_VERSION
        )

    return _azure


def supabase():

    client = getattr(_local, "supabase", None)

    if client is None:
        client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        _local.supabase = client

    return client


def openai_status(e: Exception) -> tuple[int, str] | None:
    """
    Turns an Azure or model failure into (status, message) for an
    HTTPException, or None if `e` is something else.

    Messages are written for the student reading them, not for logs.
    """

    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        AuthenticationError,
        RateLimitError,
    )

    if isinstance(e, RateLimitError):
        return 429, "The AI service is busy right now. Try again in a moment."

    if isinstance(e, AuthenticationError):
        return 502, "The AI service rejected this server's credentials."

    if isinstance(e, APITimeoutError):
        return 504, "The AI service took too long to answer. Try again."

    if isinstance(e, APIConnectionError):
        return 503, "Could not reach the AI service."

    if isinstance(e, APIError):
        return 502, "The AI service returned an error. Try again."

    if isinstance(e, ModelOutputError):
        return 502, f"{e} Try asking again."

    return None


def is_uuid(value) -> bool:

    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


# -------------------------
# Chat
# -------------------------

def chat_text(
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 600
) -> str:

    response = azure().chat.completions.create(
        model=CHAT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )

    return (response.choices[0].message.content or "").strip()


def parse_json(text: str):
    """
    Pulls a JSON value out of model output.

    Models wrap JSON in code fences or add a sentence around it even when
    told not to, so try the plain parse first and then the outermost braces.
    """

    if not text:
        raise ModelOutputError("The model returned nothing.")

    cleaned = text.strip()

    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.S | re.I)

    if fenced:
        cleaned = fenced.group(1)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ModelOutputError("The model's answer was not valid JSON.")


def chat_json(
        system: str,
        user: str,
        validate,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        attempts: int = 2
):
    """
    Asks for a JSON object and returns validate(parsed).

    `validate` takes the parsed value and returns the cleaned result, or
    raises ModelOutputError. A bad answer is retried once before giving up,
    so the caller never receives raw model text dressed up as a result.
    """

    use_json_mode = True
    last_error = ModelOutputError("The model returned nothing usable.")

    for _ in range(attempts):

        kwargs = {}

        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = azure().chat.completions.create(
                model=CHAT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

        except BadRequestError:
            # An older deployment or API version without JSON mode.
            if use_json_mode:
                use_json_mode = False
                continue
            raise

        raw = response.choices[0].message.content or ""

        try:
            return validate(parse_json(raw))
        except ModelOutputError as e:
            last_error = e

    raise last_error


# -------------------------
# Embeddings
# -------------------------

EMBED_BATCH = 16


def embed_texts(texts: list[str]) -> list[list[float]]:
    """One API call per batch of 16 instead of one per chunk."""

    vectors: list[list[float]] = []

    for i in range(0, len(texts), EMBED_BATCH):

        batch = texts[i:i + EMBED_BATCH]

        response = azure().embeddings.create(
            model=EMBEDDING_DEPLOYMENT,
            input=batch
        )

        # The API returns items in input order, but sort by index to be safe.
        ordered = sorted(response.data, key=lambda d: d.index)
        vectors.extend(d.embedding for d in ordered)

    return vectors


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


# -------------------------
# Chunking
# -------------------------

def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    """
    Splits text into roughly `size`-character chunks that end on a paragraph,
    sentence or word boundary instead of mid-word, with `overlap` characters
    repeated at the start of the next chunk so an idea that straddles a cut
    still appears whole in one of them.
    """

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    chunks: list[str] = []
    n = len(text)
    start = 0

    while start < n:

        end = min(start + size, n)

        if end < n:

            window = text[start:end]

            cut = max(
                window.rfind("\n\n"),
                window.rfind(". "),
                window.rfind("? "),
                window.rfind("! "),
                window.rfind("\n")
            )

            if cut > size * 0.5:
                end = start + cut + 1
            else:
                space = window.rfind(" ")

                if space > size * 0.5:
                    end = start + space

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= n:
            break

        start = max(end - overlap, start + 1)

        # Begin the next chunk on a word, not in the middle of one.
        if text[start - 1] not in " \n":
            space = text.find(" ", start, start + 60)

            if space != -1:
                start = space + 1

    return chunks


# -------------------------
# Retrieval
# -------------------------

def retrieve(
        course_id: str,
        user_id: str | None,
        query: str,
        k: int = 8
) -> list[dict]:
    """
    The k pieces of course material closest to `query`, as
    [{content, source, similarity}].

    What a user can see: material shared with the class, plus their own
    private uploads. A user id that is not a real account (the dev-mode
    "test-user") sees class material only.
    """

    vector = embed_text(query)

    if is_uuid(user_id):
        rows = supabase().rpc("match_course_materials", {
            "query_embedding": vector,
            "match_course_id": course_id,
            "requesting_user_id": str(user_id),
            "match_count": k
        }).execute().data or []
    else:
        rows = supabase().rpc("match_course_materials", {
            "query_embedding": vector,
            "match_course_id": course_id,
            "match_count": k
        }).execute().data or []

    if not rows:
        return []

    # The search function does not return the file name; look it up.
    ids = [r["id"] for r in rows]

    named = supabase().table("course_materials") \
        .select("id,source") \
        .in_("id", ids) \
        .execute().data or []

    source_of = {r["id"]: r["source"] for r in named}

    return [
        {
            "content": r["content"],
            "source": source_of.get(r["id"]) or "course material",
            "similarity": r.get("similarity")
        }
        for r in rows
    ]


def build_context(chunks: list[dict]) -> dict:
    """The shape the prompts expect, plus the files the answer drew on."""

    sources: list[str] = []

    for c in chunks:
        if c["source"] not in sources:
            sources.append(c["source"])

    return {
        "content_chunks": [
            f"[{c['source']}]\n{c['content']}" for c in chunks
        ],
        "sources": sources
    }
