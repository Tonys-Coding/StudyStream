import os
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import agents as agent_client
from auth import REQUIRE_AUTH, get_current_user, supabase
from router import route_all, route_request


app = FastAPI(
    title="AI Classroom Assistant Orchestrator",
    version="1.1.0"
)


# The orchestrator is the only browser-facing service. The three agents are
# called server-to-server, so they do not need CORS of their own.
FRONTEND_ORIGINS = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in FRONTEND_ORIGINS.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


if not REQUIRE_AUTH:
    print("[ORCHESTRATOR] WARNING: REQUIRE_AUTH=false — "
          "unauthenticated requests may claim any user_id. Local dev only.")


VALID_ROLES = ("teacher", "student", "ta")



class ChatRequest(BaseModel):
    message: str
    course_id: str

    # Skips keyword routing when set.
    agent: Literal["study", "quiz", "faq"] | None = None

    num_questions: int = 5

    # Dev only. Used when REQUIRE_AUTH=false and no token was sent;
    # ignored whenever there is a verified user.
    user_id: str | None = None


class AskRequest(BaseModel):
    message: str
    course_id: str

    # Overrides agent selection when set. Left empty, the orchestrator picks.
    agents: list[Literal["study", "quiz", "faq"]] | None = None

    num_questions: int = 5

    # Dev only, same as ChatRequest.
    user_id: str | None = None


class MaterialDescriptionRequest(BaseModel):
    source: str
    description: str


class ProfileSetupRequest(BaseModel):
    role: str
    full_name: str



# -------------------------
# Uniform error envelope
# -------------------------
# Every failure leaves this service as {"success": false, "message": "..."}
# so the frontend has one shape to handle.

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
):

    problems = "; ".join(
        f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": f"Invalid request: {problems}"
        }
    )



@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "orchestrator"
    }



def resolve_user_id(current_user: dict | None, body_user_id: str | None) -> str:
    """
    The verified token always wins. The body value is a dev-mode fallback.
    """

    if current_user is not None:
        return current_user["id"]

    if body_user_id:
        return body_user_id

    raise HTTPException(
        status_code=401,
        detail="No authenticated user, and no user_id was provided"
    )



def require_signed_in(current_user: dict | None) -> None:
    """
    For endpoints that need a session but not a user id.

    When REQUIRE_AUTH is true, get_current_user has already rejected an
    unauthenticated caller before this runs, so this is a no-op. When it is
    false, these endpoints stay open for local development.
    """

    if current_user is None and REQUIRE_AUTH:
        raise HTTPException(
            status_code=401,
            detail="Authentication is required"
        )



@app.post("/ask")
def ask(
        request: AskRequest,
        current_user: dict | None = Depends(get_current_user)
):
    """
    Send one message to every relevant agent and return all of their output
    plus a combined overview. Backs the workspace UI.
    """

    print("\n[ORCHESTRATOR] Received workspace query:")
    print(request.message)


    user_id = resolve_user_id(current_user, request.user_id)


    try:

        return route_all(
            message=request.message,
            user_id=user_id,
            course_id=request.course_id,
            agents=request.agents,
            num_questions=request.num_questions
        )


    except HTTPException:
        raise


    except Exception as e:

        print("[ORCHESTRATOR ERROR]", str(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



@app.post("/chat")
def chat(
        request: ChatRequest,
        current_user: dict | None = Depends(get_current_user)
):
    """
    Route a message to a single agent. Kept for direct, one-agent calls.
    """

    print("\n[ORCHESTRATOR] Received message:")
    print(request.message)


    user_id = resolve_user_id(current_user, request.user_id)


    try:

        return route_request(
            message=request.message,
            user_id=user_id,
            course_id=request.course_id,
            agent=request.agent,
            num_questions=request.num_questions
        )


    except HTTPException:
        # Already carries the agent's own status code and message
        raise


    except Exception as e:

        print("[ORCHESTRATOR ERROR]", str(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



@app.get("/materials/{course_id}")
def get_materials(
        course_id: str,
        current_user: dict | None = Depends(get_current_user)
):
    """
    What has been uploaded for a course. Drives the sidebar list and tells
    the UI whether study plans and FAQ answers are possible yet.
    """

    require_signed_in(current_user)

    return agent_client.list_materials(course_id)



@app.get("/courses")
def get_courses(current_user: dict | None = Depends(get_current_user)):
    """
    Courses that already have material ingested. The UI merges these with the
    student's own list so nothing uploaded ends up invisible.
    """

    require_signed_in(current_user)

    return agent_client.list_courses()



@app.delete("/materials/{course_id}")
def delete_material(
        course_id: str,
        source: str,
        current_user: dict | None = Depends(get_current_user)
):
    """
    Removes an uploaded file and every chunk embedded from it.
    """

    require_signed_in(current_user)

    print(f"[ORCHESTRATOR] Deleting {source} from {course_id}")

    return agent_client.delete_material(course_id, source)



@app.patch("/materials/{course_id}")
def update_material_description(
        course_id: str,
        request: MaterialDescriptionRequest,
        current_user: dict | None = Depends(get_current_user)
):
    """
    Sets the short description shown beside a file in the Overview table.
    """

    require_signed_in(current_user)

    return agent_client.set_material_description(
        course_id,
        request.source,
        request.description
    )



@app.post("/materials/upload")
async def upload_material(
        course_id: str = Form(...),
        file: UploadFile = File(...),
        current_user: dict | None = Depends(get_current_user)
):
    """
    Accepts a course document and hands it to the study agent for ingestion.
    """

    require_signed_in(current_user)

    content = await file.read()

    print(f"[ORCHESTRATOR] Uploading {file.filename} to {course_id}")

    return agent_client.upload_material(
        filename=file.filename or "upload",
        content=content,
        content_type=file.content_type,
        course_id=course_id
    )



@app.post("/profile/setup")
def setup_profile(
        request: ProfileSetupRequest,
        current_user: dict | None = Depends(get_current_user)
):

    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication is required to set up a profile"
        )


    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Role must be one of {VALID_ROLES}"
        )


    existing = supabase.table("profiles") \
        .select("id") \
        .eq("id", current_user["id"]) \
        .execute()

    if existing.data:
        raise HTTPException(
            status_code=409,
            detail="Profile already exists for this user"
        )


    supabase.table("profiles").insert({
        "id": current_user["id"],
        "role": request.role,
        "full_name": request.full_name
    }).execute()


    return {
        "success": True,
        "role": request.role
    }
