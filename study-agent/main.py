import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from pydantic import BaseModel
from models import StudyPlanRequest, StudyPlanResponse
from agent import study_and_plan_agent
from data import (
    SUPPORTED_EXTENSIONS,
    delete_material,
    get_course_context,
    ingest_file,
    list_courses,
    list_materials,
    save_upload_temporarily,
    set_material_description,
)


class MaterialDescriptionRequest(BaseModel):
    source: str
    description: str

#For extensive exception type handling
from openai import AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError, APIError

app = FastAPI(
    title = "Study Plan Generator API",
    version = "1.0.0"
)

@app.get("/health")
def read_health():
    return {"status": "healthy"}

@app.post("/study_plan", response_model=StudyPlanResponse)
def get_study_plan(study: StudyPlanRequest):

    try:
        print("STEP 1: received request")
        
        goal = study.goal.strip() if study.goal else ""

        # Checked before retrieval: get_course_context raises ValueError on an
        # empty goal, which would surface as a 500 instead of this 400.
        if not goal:
            raise HTTPException(status_code=400, detail="Missing required field: goal is required.")

        print("STEP 2: getting course context")
        course_context = get_course_context(
            study.course_id,
            goal)

        print("STEP 3: course context received")
        print(course_context)

        # get_course_context always returns a dict, so a truthiness check on it
        # passes even when retrieval found nothing. Check the chunks instead,
        # otherwise a course with no material gets a plan invented from thin air.
        if not course_context.get("content_chunks"):
            raise HTTPException(status_code=404, detail=f"No course material found for course_id: {study.course_id}. Upload material for this course first.")

        result = study_and_plan_agent(
                        user_id = study.user_id,
                        course_id = study.course_id,
                        goal = goal,
                        course_context = course_context,)
        
        
        return StudyPlanResponse(
            success=True,
            study_plan=result.get("study_plan", []),
            focus_topics=result.get("focus_topics", []),
            estimated_hours=result.get("estimated_hours", None)
        )
    
    except HTTPException:
        raise 
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {str(e)}")
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")
    except APITimeoutError as e:
        raise HTTPException(status_code=504, detail=f"API timeout: {str(e)}")
    except APIConnectionError as e:
        raise HTTPException(status_code=503, detail=f"API connection error: {str(e)}")
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Uploads are capped so a stray large PDF cannot spend an unbounded number of
# embedding calls. Raise MAX_UPLOAD_MB if your course material needs it.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024


@app.get("/courses")
def get_courses():
    return {
        "success": True,
        "courses": list_courses()
    }


@app.delete("/materials/{course_id}")
def remove_material(course_id: str, source: str):

    try:

        deleted = delete_material(course_id, source)

        return {
            "success": True,
            "source": source,
            "deleted": deleted
        }

    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/materials/{course_id}")
def get_materials(course_id: str):
    return {
        "success": True,
        "course_id": course_id,
        "materials": list_materials(course_id)
    }


@app.patch("/materials/{course_id}")
def update_material_description(
    course_id: str,
    request: MaterialDescriptionRequest
):

    try:

        updated = set_material_description(
            course_id,
            request.source,
            request.description.strip()
        )

        return {
            "success": True,
            "source": request.source,
            "updated": updated
        }


    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except RuntimeError as e:
        # The description column has not been added to the table yet.
        raise HTTPException(status_code=501, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/materials/upload")
def upload_material(
    file: UploadFile,
    course_id: str = Form(...),
    tag: str = Form("uploaded")
):

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix or filename}'. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
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
                detail=f"File is too large ({size // 1024 // 1024} MB). The limit is {MAX_UPLOAD_BYTES // 1024 // 1024} MB."
            )

        chunks = ingest_file(
            temp_path,
            course_id=course_id,
            tag=tag,
            source=filename
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
        raise HTTPException(status_code=500, detail=f"Could not ingest that file: {e}")


    finally:
        # The spooled copy is only needed for extraction.
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)