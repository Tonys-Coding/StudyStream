import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI
from supabase import create_client


# Load root .env
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


# Retrieval only. Ingesting material is the study agent's job - this agent
# reads the same course_materials table that the upload path writes to.

def embed_chunk(text: str) -> list[float]:

    response = client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT_NAME,
        input=text
    )

    return response.data[0].embedding


def retrieve_relevant_chunks(
        course_id: str,
        query: str,
        match_count: int = 5
) -> list[dict]:

    query_vector = embed_chunk(query)

    response = supabase.rpc("match_course_materials", {
        "query_embedding": query_vector,
        "match_course_id": course_id,
        "match_count": match_count
    }).execute()

    return response.data or []


def get_course_context(course_id: str, question: str) -> dict:
    """
    Pulls the course material most relevant to the student's question.

    Callers must check content_chunks: an empty list means this course has
    nothing ingested, and answering anyway would just be invention.
    """

    if not question:
        raise ValueError("A question is required to retrieve course context.")

    results = retrieve_relevant_chunks(course_id, question)

    return {
        "content_chunks": [r["content"] for r in results]
    }
