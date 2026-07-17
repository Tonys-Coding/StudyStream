from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):

    message = request.message.lower()

    print("\n[ORCHESTRATOR] Received message:", request.message)

    # Quiz route
    if "quiz" in message:
        print("[ORCHESTRATOR] Routing → Assessment Agent")

        response = requests.post(
            "http://localhost:8002/generate_quiz",
            json={
                "topic": request.message,
                "num_questions": 3
            }
        )

        print("[ORCHESTRATOR] Assessment Agent responded")

        return {
            "agent": "Assessment Agent",
            "response": response.json()
        }

    # Study route
    elif "study" in message:
        print("[ORCHESTRATOR] Routing → Study Agent")

        response = requests.post(
            "http://localhost:8003/study_plan",
            json={
                "topic": request.message,
                "days_until_exam": 7
            }
        )

        print("[ORCHESTRATOR] Study Agent responded")

        return {
            "agent": "Study Agent",
            "response": response.json()
        }

    # Default FAQ route
    else:
        print("[ORCHESTRATOR] Routing → FAQ Agent")

        response = requests.post(
            "http://localhost:8000/faq",
            json={
                "question": request.message
            }
        )

        print("[ORCHESTRATOR] FAQ Agent responded")

        return {
            "agent": "FAQ Agent",
            "response": response.json()
        }