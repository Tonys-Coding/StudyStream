import hmac
import os
import sys
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import STAFF_ROLES, supabase

import agents as agent_client
import store
from auth import REQUIRE_AUTH, get_current_user
from router import route_all, route_request


app = FastAPI(
    title="AI Classroom Assistant Orchestrator",
    version="2.0.0"
)


# The orchestrator is the only browser-facing service. The three agents are
# called server-to-server, so they do not need CORS of their own.
FRONTEND_ORIGINS = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
)

# Anything that is not already an HTTPException ends up here. The detail goes
# to the log; the caller gets a message that leaks no hostnames or stack
# frames. This is middleware rather than an exception handler, and it is added
# before CORS so it sits inside it: a handler registered for Exception runs
# outside CORS, so its response would carry no CORS headers and the browser
# would hide the message behind a generic "Load failed".
@app.middleware("http")
async def catch_unexpected(request: Request, call_next):

    try:
        return await call_next(request)

    except Exception as e:

        print("[ORCHESTRATOR ERROR]", type(e).__name__, e)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Something went wrong on the server. Please try again."
            }
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

# Teacher and TA accounts can share material with a whole class, so they are
# not self-service: signing up as one needs this code, which the person
# running the server hands out. Unset means nobody can claim those roles.
TEACHER_INVITE_CODE = os.getenv("TEACHER_INVITE_CODE", "").strip()

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024



class ChatRequest(BaseModel):
    message: str
    course_id: str

    # Skips keyword routing when set.
    agent: Literal["study", "quiz", "faq"] | None = None

    num_questions: int = Field(default=5, ge=1, le=20)

    # Dev only. Used when REQUIRE_AUTH=false and no token was sent;
    # ignored whenever there is a verified user.
    user_id: str | None = None


class AskRequest(BaseModel):
    message: str
    course_id: str

    # Overrides agent selection when set. Left empty, the orchestrator picks.
    agents: list[Literal["study", "quiz", "faq"]] | None = None

    num_questions: int = Field(default=5, ge=1, le=20)

    # Dev only, same as ChatRequest.
    user_id: str | None = None


class MaterialDescriptionRequest(BaseModel):
    source: str
    description: str
    visibility: Literal["class", "private"] = "private"


class ProfileSetupRequest(BaseModel):
    role: str
    full_name: str
    invite_code: str | None = None


class CourseRequest(BaseModel):
    id: str
    name: str | None = None

    # Teachers only: show this subject to the students linked to them.
    public: bool = False


class AssignmentRequest(BaseModel):
    title: str
    course_id: str | None = None
    due_date: str | None = None


class AssignmentPatch(BaseModel):
    title: str | None = None
    course_id: str | None = None
    due_date: str | None = None
    done: bool | None = None


class TeacherCodeRequest(BaseModel):
    code: str


class QuizResultRequest(BaseModel):
    course_id: str
    topic: str = ""
    score: int = Field(ge=0)
    total: int = Field(ge=1, le=50)



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



# -------------------------
# Who is calling
# -------------------------

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


def actor(current_user: dict | None) -> tuple[str | None, str | None]:
    """
    (user id, role) for the material endpoints.

    With auth off and no token there is no user. That dev caller is treated
    as a teacher, so the test script and /docs can exercise everything.
    """

    if current_user is None:
        return None, "teacher"

    return current_user["id"], current_user["role"]


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


def require_user(current_user: dict | None) -> dict:
    """For endpoints about the caller themselves, which have no dev fallback."""

    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="Sign in to use this."
        )

    return current_user


def require_member(current_user: dict | None, course_id: str) -> None:
    """
    A signed-in user may only work in subjects they have added, or public ones.
    Without this anyone could read or change a private course by guessing its
    code.
    """

    if current_user is None:
        return

    if not store.ensure_access(current_user["id"], course_id):
        raise HTTPException(
            status_code=403,
            detail=f"Add {course_id} to your subjects first."
        )



# -------------------------
# Asking
# -------------------------

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

    require_member(current_user, request.course_id)


    result = route_all(
        message=request.message,
        user_id=user_id,
        course_id=request.course_id,
        agents=request.agents,
        num_questions=request.num_questions
    )

    store.log_ask(user_id, request.course_id, request.message)

    # Kept so the student can reopen this answer later. None when it could
    # not be saved (dev mode, or the migration has not been run).
    result["session_id"] = store.save_session(
        user_id, request.course_id, request.message, dict(result)
    )

    return result



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

    require_member(current_user, request.course_id)


    return route_request(
        message=request.message,
        user_id=user_id,
        course_id=request.course_id,
        agent=request.agent,
        num_questions=request.num_questions
    )



# -------------------------
# Course material
# -------------------------

@app.get("/materials/{course_id}")
def get_materials(
        course_id: str,
        current_user: dict | None = Depends(get_current_user)
):
    """
    The files this user can see in a course: material shared with the class,
    plus their own private uploads.
    """

    require_signed_in(current_user)
    require_member(current_user, course_id)

    user_id, role = actor(current_user)

    return agent_client.list_materials(course_id, user_id, role)



@app.delete("/materials/{course_id}")
def delete_material(
        course_id: str,
        source: str,
        visibility: Literal["class", "private"] = "private",
        current_user: dict | None = Depends(get_current_user)
):
    """
    Removes an uploaded file and every chunk embedded from it. Students can
    remove their own files; shared files need a teacher or TA.
    """

    require_signed_in(current_user)
    require_member(current_user, course_id)

    user_id, role = actor(current_user)

    print(f"[ORCHESTRATOR] Deleting {source} from {course_id}")

    return agent_client.delete_material(
        course_id, source, visibility, user_id, role
    )



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
    require_member(current_user, course_id)

    user_id, role = actor(current_user)

    return agent_client.set_material_description(
        course_id,
        request.source,
        request.description,
        request.visibility,
        user_id,
        role
    )



@app.post("/materials/upload")
async def upload_material(
        course_id: str = Form(...),
        file: UploadFile = File(...),
        current_user: dict | None = Depends(get_current_user)
):
    """
    Accepts a course document and hands it to the study agent for ingestion.
    A student's upload is private to them; a teacher's or TA's is shared with
    the class.
    """

    require_signed_in(current_user)
    require_member(current_user, course_id)

    user_id, role = actor(current_user)

    too_big = HTTPException(
        status_code=413,
        detail=f"File is too large. The limit is {MAX_UPLOAD_BYTES // 1024 // 1024} MB."
    )

    # Refuse early when the size is declared, and otherwise stop reading the
    # moment the limit is passed, so a huge file never sits whole in memory.
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise too_big

    content = bytearray()

    while True:

        piece = await file.read(1024 * 1024)

        if not piece:
            break

        content.extend(piece)

        if len(content) > MAX_UPLOAD_BYTES:
            raise too_big

    print(f"[ORCHESTRATOR] Uploading {file.filename} to {course_id}")

    return agent_client.upload_material(
        filename=file.filename or "upload",
        content=bytes(content),
        content_type=file.content_type,
        course_id=course_id,
        user_id=user_id,
        role=role
    )



# -------------------------
# Profile
# -------------------------

@app.get("/me")
def me(current_user: dict | None = Depends(get_current_user)):
    """
    The signed-in user's profile. has_profile is false for an account that
    signed up but never finished setup, which the UI uses to ask for it.
    """

    user = require_user(current_user)

    return {
        "success": True,
        "id": user["id"],
        "has_profile": user["role"] is not None,
        "role": user["role"],
        "full_name": user["full_name"]
    }



@app.post("/profile/setup")
def setup_profile(
        request: ProfileSetupRequest,
        current_user: dict | None = Depends(get_current_user)
):

    user = require_user(current_user)


    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Role must be one of {VALID_ROLES}"
        )


    full_name = request.full_name.strip()

    if not full_name or len(full_name) > 100:
        raise HTTPException(
            status_code=400,
            detail="Enter your name (up to 100 characters)."
        )


    if request.role in STAFF_ROLES:

        if not TEACHER_INVITE_CODE:
            raise HTTPException(
                status_code=403,
                detail="Teacher and TA accounts are not enabled on this server."
            )

        if not hmac.compare_digest(
                (request.invite_code or "").strip().encode(),
                TEACHER_INVITE_CODE.encode()
        ):
            raise HTTPException(
                status_code=403,
                detail="That invite code is not valid."
            )


    existing = supabase().table("profiles") \
        .select("id") \
        .eq("id", user["id"]) \
        .execute()

    if existing.data:
        raise HTTPException(
            status_code=409,
            detail="Profile already exists for this user"
        )


    supabase().table("profiles").insert({
        "id": user["id"],
        "role": request.role,
        "full_name": full_name
    }).execute()


    return {
        "success": True,
        "role": request.role,
        "full_name": full_name
    }



# -------------------------
# Subjects
# -------------------------

@app.get("/courses")
def get_courses(current_user: dict | None = Depends(get_current_user)):
    """
    The subjects this user has added. Lives in the database, so it follows
    them to any browser or device.
    """

    require_signed_in(current_user)

    if current_user is None:
        return {"success": True, "courses": []}

    return {
        "success": True,
        "courses": store.list_my_courses(current_user["id"])
    }



@app.post("/courses")
def add_course(
        request: CourseRequest,
        current_user: dict | None = Depends(get_current_user)
):
    """
    Adds a subject to the user's list. A code nobody has used yet creates the
    course; one that exists is simply joined.
    """

    user = require_user(current_user)

    return {
        "success": True,
        "course": store.add_course(
            user["id"], request.id, request.name, request.public, user["role"]
        )
    }



@app.delete("/courses/{course_id}")
def remove_course(
        course_id: str,
        current_user: dict | None = Depends(get_current_user)
):
    """Drops a subject from the user's list. Uploaded files are kept."""

    user = require_user(current_user)

    store.remove_course(user["id"], course_id)

    return {"success": True}



# -------------------------
# Activity and dashboard
# -------------------------

@app.post("/activity/quiz")
def record_quiz(
        request: QuizResultRequest,
        current_user: dict | None = Depends(get_current_user)
):
    """Saves a finished practice quiz so progress shows on the Dashboard."""

    user = require_user(current_user)

    if request.score > request.total:
        raise HTTPException(
            status_code=400,
            detail="Score cannot be higher than the number of questions."
        )

    require_member(user, request.course_id)

    store.log_quiz(
        user["id"],
        request.course_id,
        request.topic,
        request.score,
        request.total
    )

    return {"success": True}



@app.get("/dashboard")
def dashboard(current_user: dict | None = Depends(get_current_user)):
    """
    The caller's own progress, plus class-wide totals for teachers and TAs.
    """

    user = require_user(current_user)

    return store.build_dashboard(user["id"], user["role"])



# -------------------------
# Chat sessions
# -------------------------

@app.get("/sessions")
def list_sessions(
        course_id: str,
        current_user: dict | None = Depends(get_current_user)
):
    """Past questions for one subject, newest first."""

    user = require_user(current_user)

    return {
        "success": True,
        "sessions": store.list_sessions(user["id"], course_id)
    }



@app.get("/sessions/{session_id}")
def get_session(
        session_id: str,
        current_user: dict | None = Depends(get_current_user)
):
    """One past question with its full answer, as /ask returned it."""

    user = require_user(current_user)

    return {
        "success": True,
        "session": store.get_session(user["id"], session_id)
    }



@app.delete("/sessions/{session_id}")
def delete_session(
        session_id: str,
        current_user: dict | None = Depends(get_current_user)
):

    user = require_user(current_user)

    store.delete_session(user["id"], session_id)

    return {"success": True}



# -------------------------
# Assignments
# -------------------------
# Personal to-do items: only ever the caller's own.

@app.get("/assignments")
def list_assignments(current_user: dict | None = Depends(get_current_user)):

    user = require_user(current_user)

    return {
        "success": True,
        "assignments": store.list_assignments(user["id"])
    }



@app.post("/assignments")
def add_assignment(
        request: AssignmentRequest,
        current_user: dict | None = Depends(get_current_user)
):

    user = require_user(current_user)

    return {
        "success": True,
        "assignment": store.add_assignment(
            user["id"], request.title, request.course_id, request.due_date
        )
    }



@app.patch("/assignments/{assignment_id}")
def update_assignment(
        assignment_id: int,
        request: AssignmentPatch,
        current_user: dict | None = Depends(get_current_user)
):

    user = require_user(current_user)

    return {
        "success": True,
        "assignment": store.update_assignment(
            user["id"],
            assignment_id,
            request.model_dump(exclude_unset=True)
        )
    }



@app.delete("/assignments/{assignment_id}")
def delete_assignment(
        assignment_id: int,
        current_user: dict | None = Depends(get_current_user)
):

    user = require_user(current_user)

    store.delete_assignment(user["id"], assignment_id)

    return {"success": True}



# -------------------------
# Teachers
# -------------------------
# A teacher has a personal code. Students and TAs enter it to see that
# teacher's shared subjects and a short summary of the teacher.

@app.get("/teacher/code")
def teacher_code(current_user: dict | None = Depends(get_current_user)):
    """The signed-in teacher's own code and how many people have linked."""

    user = require_user(current_user)

    if user["role"] != "teacher":
        raise HTTPException(
            status_code=403,
            detail="Only teachers have a teacher code."
        )

    return {"success": True, **store.get_teacher_code(user["id"])}



@app.get("/teacher/roster")
def teacher_roster(current_user: dict | None = Depends(get_current_user)):
    """The students and TAs linked to the signed-in teacher."""

    user = require_user(current_user)

    if user["role"] != "teacher":
        raise HTTPException(
            status_code=403,
            detail="Only teachers can see who is linked to them."
        )

    return {"success": True, "people": store.list_roster(user["id"])}



@app.get("/teachers")
def list_teachers(current_user: dict | None = Depends(get_current_user)):
    """The teachers this user has linked to, with their shared subjects."""

    user = require_user(current_user)

    return {"success": True, "teachers": store.list_teachers(user["id"])}



@app.post("/teachers/link")
def link_teacher(
        request: TeacherCodeRequest,
        current_user: dict | None = Depends(get_current_user)
):

    user = require_user(current_user)

    return {
        "success": True,
        "teacher": store.link_teacher(user["id"], user["role"], request.code)
    }



@app.delete("/teachers/{teacher_id}")
def unlink_teacher(
        teacher_id: str,
        current_user: dict | None = Depends(get_current_user)
):
    """Stops following a teacher. Their shared subjects leave the sidebar."""

    user = require_user(current_user)

    store.unlink_teacher(user["id"], teacher_id)

    return {"success": True}
