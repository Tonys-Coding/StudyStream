import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load .env
# load_dotenv(Path(__file__).parent / ".env")
script_dir = Path(__file__).parent
load_dotenv(script_dir / ".env")

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)

DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT_NAME")


def ai_route_query(query: str):

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
You are an AI router for a classroom assistant.

Choose which agents should answer the user's request.

Available agents:

faq
- explanations
- definitions
- how/why questions
- conceptual questions

quiz
- quizzes
- practice questions
- assessments
- flashcards
- tests

study
- study plans
- schedules
- exam preparation
- learning roadmaps

Return ONLY JSON in this format:

{
    "agents": ["faq", "study"]
}
"""
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )

    result = json.loads(response.choices[0].message.content)

    return result["agents"]
