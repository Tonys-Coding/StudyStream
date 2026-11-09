import os

import requests
from fastapi import HTTPException


# Agent URLs
# Overridable so the agents can move off localhost without a code change.

STUDY_AGENT_URL = os.getenv(
    "STUDY_AGENT_URL",
    "http://127.0.0.1:8003/study_plan"
)

# Same service as STUDY_AGENT_URL - it owns course material.
STUDY_AGENT_BASE = os.getenv(
    "STUDY_AGENT_BASE",
    "http://127.0.0.1:8003"
)

ASSESSMENT_AGENT_URL = os.getenv(
    "ASSESSMENT_AGENT_URL",
    "http://127.0.0.1:8002/generate_quiz"
)

FAQ_AGENT_URL = os.getenv(
    "FAQ_AGENT_URL",
    "http://127.0.0.1:8000/faq"
)


# Azure calls are slow, so give the agents room before giving up.
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "90"))



def _send(
        method: str,
        url: str,
        agent_name: str,
        timeout: int = AGENT_TIMEOUT,
        **kwargs
):
    """
    Calls an agent and passes its error message back up.

    Without this, an agent responding "no content found for course X"
    reaches the browser as an opaque 500 with nothing to debug from.
    """

    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="StudyStream is unavailable for a moment. Please try again shortly."
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="That took too long. Please try again."
        )


    if response.status_code >= 400:

        # Agents report failures as {"detail": "..."}; fall back to the raw
        # body if this one did something else.
        detail = response.text

        try:
            body = response.json()
            detail = body.get("detail") or body.get("message") or detail
        except ValueError:
            pass

        raise HTTPException(
            status_code=response.status_code,
            detail=detail
        )


    return response.json()



# -------------------------
# Study Agent
# -------------------------

def call_study_agent(
        user_id: str,
        course_id: str,
        goal: str
):

    return _send(
        "POST",
        STUDY_AGENT_URL,
        "Study Agent",
        json={
            "user_id": user_id,
            "course_id": course_id,
            "goal": goal
        }
    )



# -------------------------
# Assessment Agent
# -------------------------

def call_assessment_agent(
        user_id: str,
        course_id: str,
        topic: str,
        num_questions: int = 5
):

    return _send(
        "POST",
        ASSESSMENT_AGENT_URL,
        "Assessment Agent",
        json={
            "user_id": user_id,
            "course_id": course_id,
            "topic": topic,
            "num_questions": num_questions
        }
    )



# -------------------------
# FAQ Agent
# -------------------------

def call_faq_agent(question: str, course_id: str, user_id: str | None = None):

    return _send(
        "POST",
        FAQ_AGENT_URL,
        "FAQ Agent",
        json={
            "question": question,
            "course_id": course_id,
            "user_id": user_id
        }
    )



# -------------------------
# Course materials
# -------------------------
#
# The study agent owns these. Every call says who is asking and in what role,
# because that decides which files they can see and change.

def _who(user_id: str | None, role: str | None) -> dict:
    return {"user_id": user_id or "", "role": role or ""}


def list_materials(course_id: str, user_id: str | None, role: str | None):

    return _send(
        "GET",
        f"{STUDY_AGENT_BASE}/materials/{course_id}",
        "Study Agent",
        timeout=30,
        params={k: v for k, v in _who(user_id, role).items() if v}
    )


def delete_material(
        course_id: str,
        source: str,
        visibility: str,
        user_id: str | None,
        role: str | None
):

    return _send(
        "DELETE",
        f"{STUDY_AGENT_BASE}/materials/{course_id}",
        "Study Agent",
        timeout=30,
        params={
            "source": source,
            "visibility": visibility,
            **{k: v for k, v in _who(user_id, role).items() if v}
        }
    )


def set_material_description(
        course_id: str,
        source: str,
        description: str,
        visibility: str,
        user_id: str | None,
        role: str | None
):

    return _send(
        "PATCH",
        f"{STUDY_AGENT_BASE}/materials/{course_id}",
        "Study Agent",
        timeout=30,
        json={
            "source": source,
            "description": description,
            "visibility": visibility,
            "user_id": user_id,
            "role": role
        }
    )


def upload_material(
        filename: str,
        content: bytes,
        content_type: str | None,
        course_id: str,
        user_id: str | None,
        role: str | None,
        tag: str = "uploaded"
):
    """
    Forwards an uploaded file on to the study agent, which does the
    extraction, chunking, and embedding.
    """

    return _send(
        "POST",
        f"{STUDY_AGENT_BASE}/materials/upload",
        "Study Agent",
        timeout=AGENT_TIMEOUT * 4,  # embedding every chunk takes a while
        files={
            "file": (filename, content, content_type or "application/octet-stream")
        },
        data={
            "course_id": course_id,
            "tag": tag,
            **{k: v for k, v in _who(user_id, role).items() if v}
        }
    )
