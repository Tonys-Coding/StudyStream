from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI

from agent import answer_faq
from models import FAQRequest

app = FastAPI()


@app.post("/faq")
def faq(request: FAQRequest):
    query = request.student_query
    print(
        "[FAQ AGENT] Received request:",
        {
            "user_id": request.user_id,
            "course_id": request.course_id,
            "query": query,
        },
    )

    response = answer_faq(
        query,
        user_id=request.user_id,
        course_id=request.course_id,
    )

    print("[FAQ AGENT] Sending response")
    return response
