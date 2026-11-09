import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import build_context, openai_status, retrieve
from models import QuizRequest, QuizResponse
from agent import assessment_agent


app = FastAPI(
    title="Assessment Agent API",
    version="2.0.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "Assessment Agent"
    }


@app.post("/generate_quiz", response_model=QuizResponse)
def generate_quiz(request: QuizRequest):

    topic = request.topic.strip()

    if not topic:
        raise HTTPException(
            status_code=400,
            detail="Missing required field: topic is required."
        )

    try:

        # More material than the FAQ needs: a quiz should span the topic.
        context = build_context(
            retrieve(request.course_id, request.user_id, topic, k=10)
        )

        if not context["content_chunks"]:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No course material found for {request.course_id}. "
                    "Upload material for this course first."
                )
            )

        questions = assessment_agent(
            course_id=request.course_id,
            topic=topic,
            num_questions=request.num_questions,
            course_context=context
        )

        return QuizResponse(
            success=True,
            questions=questions,
            sources=context["sources"]
        )

    except HTTPException:
        raise

    except Exception as e:

        mapped = openai_status(e)

        if mapped:
            raise HTTPException(status_code=mapped[0], detail=mapped[1])

        print("[ASSESSMENT AGENT ERROR]", type(e).__name__, e)

        raise HTTPException(
            status_code=500,
            detail="Something went wrong on the server. Please try again."
        )
