import httpx

FAQ_AGENT_URL = "http://localhost:8000"
QUIZ_AGENT_URL = "http://localhost:8002"
STUDY_AGENT_URL = "http://localhost:8003"


async def call_agent(agent: str, query: str):
    async with httpx.AsyncClient() as client:

        if agent == "faq":
            res = await client.post(
                f"{FAQ_AGENT_URL}/faq",
                json={"question": query}
            )
            return res.json()

        elif agent == "quiz":
            res = await client.post(
                f"{QUIZ_AGENT_URL}/generate_quiz",
                json={
                    "topic": query,
                    "num_questions": 3
                }
            )
            return res.json()

        elif agent == "study":
            res = await client.post(
                f"{STUDY_AGENT_URL}/study/plan",
                json={
                    "user_id": "demo-user",
                    "course_id": "CS3354",
                    "goal": query
                }
            )
            return res.json()

    return {"error": "Unknown agent"}
