import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import openai_status
from models import FAQRequest, FAQResponse
from agent import faq_agent
from data import get_course_context


app = FastAPI(
    title="FAQ Agent API",
    version="2.0.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "FAQ Agent"
    }


@app.post("/faq", response_model=FAQResponse)
def faq(request: FAQRequest):

    question = request.question.strip() if request.question else ""

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Missing required field: question is required."
        )

    try:

        course_context = get_course_context(
            request.course_id,
            request.user_id,
            question
        )

        # Nothing visible for this course means there is nothing to answer
        # from, and answering anyway would just be invention.
        if not course_context["content_chunks"]:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No course material found for {request.course_id}. "
                    "Upload material for this course first."
                )
            )

        answer = faq_agent(
            question=question,
            course_context=course_context
        )

        return FAQResponse(
            success=True,
            answer=answer,
            sources=course_context["sources"]
        )

    except HTTPException:
        raise

    except Exception as e:

        mapped = openai_status(e)

        if mapped:
            raise HTTPException(status_code=mapped[0], detail=mapped[1])

        print("[FAQ AGENT ERROR]", type(e).__name__, e)

        raise HTTPException(
            status_code=500,
            detail="Something went wrong on the server. Please try again."
        )
