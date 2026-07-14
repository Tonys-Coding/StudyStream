from fastapi import FastAPI
from pydantic import BaseModel
import asyncio

from ai_router import ai_route_query
from client import call_agent

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(request: ChatRequest):

    agents = ai_route_query(request.message)

    tasks = [
        call_agent(agent, request.message)
        for agent in agents
    ]

    responses = await asyncio.gather(*tasks)

    results = []

    for agent, response in zip(agents, responses):
        results.append({
            "agent": agent,
            "output": response
        })

    return {
        "query": request.message,
        "results": results
    }
