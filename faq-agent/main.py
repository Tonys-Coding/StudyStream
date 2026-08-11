from fastapi import FastAPI, HTTPException

from openai import (
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIError
)

from models import FAQRequest, FAQResponse
from agent import faq_agent
from data import get_course_context


app = FastAPI(
    title="FAQ Agent API",
    version="1.0.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "FAQ Agent"
    }


@app.post("/faq", response_model=FAQResponse)
def faq(request: FAQRequest):

    print("[FAQ AGENT] Received question:", request.question)

    try:

        question = request.question.strip() if request.question else ""

        if not question:
            raise HTTPException(
                status_code=400,
                detail="Missing required field: question is required."
            )


        course_context = get_course_context(
            request.course_id,
            question
        )


        # Nothing ingested for this course means there is nothing to answer
        # from, and answering anyway would just be invention.
        if not course_context.get("content_chunks"):
            raise HTTPException(
                status_code=404,
                detail=f"No course material found for course_id: {request.course_id}. Upload material for this course first."
            )


        answer = faq_agent(
            question=question,
            course_context=course_context
        )

        print("[FAQ AGENT] Sending response")

        return FAQResponse(
            success=True,
            answer=answer
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
