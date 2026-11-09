import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import build_context, retrieve


# Retrieval only. Ingesting material is the study agent's job - this agent
# reads the same course_materials table that the upload path writes to.

def get_course_context(
        course_id: str,
        user_id: str | None,
        question: str
) -> dict:
    """
    Pulls the course material most relevant to the student's question,
    limited to what they are allowed to see.

    Callers must check content_chunks: an empty list means nothing visible is
    ingested for this course, and answering anyway would just be invention.
    """

    if not question:
        raise ValueError("A question is required to retrieve course context.")

    return build_context(retrieve(course_id, user_id, question, k=8))
