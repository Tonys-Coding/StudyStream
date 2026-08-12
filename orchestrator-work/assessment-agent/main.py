from fastapi import FastAPI, HTTPException

from models import QuizRequest, QuizResponse
from agent import assessment_agent


app = FastAPI(
    title="Assessment Agent API",
    version="1.0.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "Assessment Agent"
    }


@app.post("/generate_quiz", response_model=QuizResponse)
def generate_quiz(request: QuizRequest):

    try:

        result = assessment_agent(
            user_id=request.user_id,
            course_id=request.course_id,
            topic=request.topic,
            num_questions=request.num_questions
        )


        if "error" in result:
            raise HTTPException(
                status_code=404,
                detail=result["error"]
            )


        return QuizResponse(
            success=True,
            questions=result.get("questions", [])
        )


    except HTTPException:
        raise


    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )