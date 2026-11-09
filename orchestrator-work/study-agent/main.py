import os
import sys
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import openai_status, supabase
from models import StudyPlanRequest, StudyPlanResponse
from agent import study_and_plan_agent
from data import (
    SUPPORTED_EXTENSIONS,
    delete_material,
    get_course_context,
    ingest_file,
    list_materials,
    save_upload_temporarily,
    set_material_description,
)


app = FastAPI(
    title="Study Plan Generator API",
    version="2.0.0"
)


# Uploads are capped so a stray large PDF cannot spend an unbounded number of
# embedding calls. Raise MAX_UPLOAD_MB if your course material needs it.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024


class MaterialDescriptionRequest(BaseModel):
    source: str
    description: str
    visibility: str = "private"
    user_id: str | None = None
    role: str | None = None


def fail(e: Exception):
    """Maps any unexpected failure onto an HTTPException."""

    mapped = openai_status(e)

    if mapped:
        raise HTTPException(status_code=mapped[0], detail=mapped[1])

    print("[STUDY AGENT ERROR]", type(e).__name__, e)

    raise HTTPException(
        status_code=500,
        detail="Something went wrong on the server. Please try again."
    )


@app.get("/health")
def read_health():
    return {"status": "healthy"}


@app.post("/study_plan", response_model=StudyPlanResponse)
def get_study_plan(study: StudyPlanRequest):

    goal = study.goal.strip() if study.goal else ""

    # Checked before retrieval: get_course_context raises ValueError on an
    # empty goal, which would surface as a 500 instead of this 400.
    if not goal:
        raise HTTPException(
            status_code=400,
            detail="Missing required field: goal is required."
        )

    try:

        course_context = get_course_context(
            study.course_id,
            study.user_id,
            goal
        )

        # Retrieval can find nothing. Planning anyway would invent a course.
        if not course_context["content_chunks"]:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No course material found for {study.course_id}. "
                    "Upload material for this course first."
                )
            )

        result = study_and_plan_agent(
            user_id=study.user_id,
            course_id=study.course_id,
            goal=goal,
            course_context=course_context
        )

        return StudyPlanResponse(
            success=True,
            study_plan=result["study_plan"],
            focus_topics=result["focus_topics"],
            estimated_hours=result["estimated_hours"],
            sources=course_context["sources"]
        )

    except HTTPException:
        raise

    except Exception as e:
        fail(e)


@app.get("/courses")
def get_courses():
    """Courses that have any material ingested. Kept for the test script."""

    try:

        rows = supabase().table("course_materials") \
            .select("course_id") \
            .execute().data or []

        counts: dict[str, int] = {}

        for row in rows:
            counts[row["course_id"]] = counts.get(row["course_id"], 0) + 1

        return {
            "success": True,
            "courses": [
                {"course_id": c, "chunks": n}
                for c, n in sorted(counts.items())
            ]
        }

    except Exception as e:
        fail(e)


@app.get("/materials/{course_id}")
def get_materials(
    course_id: str,
    user_id: str | None = None,
    role: str | None = None
):

    try:

        return {
            "success": True,
            "course_id": course_id,
            "materials": list_materials(course_id, user_id, role)
        }

    except Exception as e:
        fail(e)


@app.delete("/materials/{course_id}")
def remove_material(
    course_id: str,
    source: str,
    visibility: str = "private",
    user_id: str | None = None,
    role: str | None = None
):

    try:

        deleted = delete_material(course_id, source, visibility, user_id, role)

        return {
            "success": True,
            "source": source,
            "deleted": deleted
        }

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        fail(e)


@app.patch("/materials/{course_id}")
def update_material_description(
    course_id: str,
    request: MaterialDescriptionRequest
):

    try:

        updated = set_material_description(
            course_id,
            request.source,
            request.description.strip(),
            request.visibility,
            request.user_id,
            request.role
        )

        return {
            "success": True,
            "source": request.source,
            "updated": updated
        }

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except RuntimeError as e:
        # The description column has not been added to the table yet.
        raise HTTPException(status_code=501, detail=str(e))

    except Exception as e:
        fail(e)


@app.post("/materials/upload")
def upload_material(
    file: UploadFile,
    course_id: str = Form(...),
    tag: str = Form("uploaded"),
    user_id: str | None = Form(None),
    role: str | None = Form(None)
):

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{suffix or filename}'. "
                f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        )

    temp_path = None

    try:

        temp_path = save_upload_temporarily(file)

        size = os.path.getsize(temp_path)

        if size == 0:
            raise HTTPException(status_code=400, detail="That file is empty.")

        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File is too large ({size // 1024 // 1024} MB). "
                    f"The limit is {MAX_UPLOAD_BYTES // 1024 // 1024} MB."
                )
            )

        chunks = ingest_file(
            temp_path,
            course_id=course_id,
            source=filename,
            user_id=user_id,
            role=role,
            tag=tag
        )

        return {
            "success": True,
            "source": filename,
            "course_id": course_id,
            "chunks": chunks
        }

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        fail(e)

    finally:
        # The spooled copy is only needed for extraction.
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
