from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class QuizRequest(BaseModel):
    topic: str
    num_questions: int = 3


@app.post("/generate_quiz")
def generate_quiz(request: QuizRequest):

    print("[ASSESSMENT AGENT] Topic:", request.topic)

    quiz = [
        f"Question {i+1} about {request.topic}"
        for i in range(request.num_questions)
    ]

    print("[ASSESSMENT AGENT] Quiz generated")

    return {
        "topic": request.topic,
        "quiz": quiz
    }