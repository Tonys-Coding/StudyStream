from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class FAQRequest(BaseModel):
    question: str


@app.post("/faq")
def faq(request: FAQRequest):

    print("[FAQ AGENT] Received question:", request.question)

    answer = f"Received question: {request.question}"

    print("[FAQ AGENT] Sending response")

    return {
        "answer": answer
    }