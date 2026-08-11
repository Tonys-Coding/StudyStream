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



def _post(url: str, payload: dict, agent_name: str) -> dict:
    """
    Send a request to an agent and pass its error message back up.

    Without this, an agent responding "no content found for course X"
    reaches the browser as an opaque 500 with nothing to debug from.
    """

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=AGENT_TIMEOUT
        )

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail=f"{agent_name} is not reachable at {url}. Is it running?"
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail=f"{agent_name} timed out after {AGENT_TIMEOUT}s"
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
            detail=f"{agent_name}: {detail}"
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

    return _post(
        STUDY_AGENT_URL,
        {
            "user_id": user_id,
            "course_id": course_id,
            "goal": goal
        },
        "Study Agent"
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

    return _post(
        ASSESSMENT_AGENT_URL,
        {
            "user_id": user_id,
            "course_id": course_id,
            "topic": topic,
            "num_questions": num_questions
        },
        "Assessment Agent"
    )



# -------------------------
# FAQ Agent
# -------------------------

def call_faq_agent(question: str, course_id: str):

    return _post(
        FAQ_AGENT_URL,
        {
            "question": question,
            "course_id": course_id
        },
        "FAQ Agent"
    )



# -------------------------
# Course materials
# -------------------------

def list_materials(course_id: str):

    try:
        response = requests.get(
            f"{STUDY_AGENT_BASE}/materials/{course_id}",
            timeout=30
        )

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail=f"Study Agent is not reachable at {STUDY_AGENT_BASE}. Is it running?"
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Study Agent: {response.text}"
        )

    return response.json()


def _study_agent_request(method: str, path: str, **kwargs):
    """
    Calls the study agent's material endpoints and passes its errors through.
    """

    try:
        response = requests.request(
            method,
            f"{STUDY_AGENT_BASE}{path}",
            timeout=30,
            **kwargs
        )

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail=f"Study Agent is not reachable at {STUDY_AGENT_BASE}. Is it running?"
        )

    if response.status_code >= 400:

        detail = response.text

        try:
            body = response.json()
            detail = body.get("detail") or body.get("message") or detail
        except ValueError:
            pass

        raise HTTPException(status_code=response.status_code, detail=str(detail))

    return response.json()


def list_courses():

    return _study_agent_request("GET", "/courses")


def delete_material(course_id: str, source: str):

    return _study_agent_request(
        "DELETE",
        f"/materials/{course_id}",
        params={"source": source}
    )


def set_material_description(course_id: str, source: str, description: str):

    try:
        response = requests.patch(
            f"{STUDY_AGENT_BASE}/materials/{course_id}",
            json={"source": source, "description": description},
            timeout=30
        )

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail=f"Study Agent is not reachable at {STUDY_AGENT_BASE}. Is it running?"
        )

    if response.status_code >= 400:

        detail = response.text

        try:
            body = response.json()
            detail = body.get("detail") or body.get("message") or detail
        except ValueError:
            pass

        raise HTTPException(status_code=response.status_code, detail=str(detail))

    return response.json()


def upload_material(
        filename: str,
        content: bytes,
        content_type: str | None,
        course_id: str,
        tag: str = "uploaded"
):
    """
    Forwards an uploaded file on to the study agent, which does the
    extraction, chunking, and embedding.
    """

    try:
        response = requests.post(
            f"{STUDY_AGENT_BASE}/materials/upload",
            files={
                "file": (filename, content, content_type or "application/octet-stream")
            },
            data={
                "course_id": course_id,
                "tag": tag
            },
            timeout=AGENT_TIMEOUT * 4  # embedding every chunk takes a while
        )

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail=f"Study Agent is not reachable at {STUDY_AGENT_BASE}. Is it running?"
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Study Agent timed out while ingesting that file."
        )

    if response.status_code >= 400:

        detail = response.text

        try:
            body = response.json()
            detail = body.get("detail") or body.get("message") or detail
        except ValueError:
            pass

        raise HTTPException(
            status_code=response.status_code,
            detail=str(detail)
        )

    return response.json()
