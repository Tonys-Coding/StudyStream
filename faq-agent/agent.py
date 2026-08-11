import os
from pathlib import Path

from openai import AzureOpenAI
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT, build_user_prompt


# Load root .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)


DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")


def faq_agent(question: str, course_context: dict) -> str:
    """
    Answers a course question from retrieved material.

    Takes the context as an argument rather than fetching it, so the caller
    can check for empty retrieval first and we only embed the question once.
    """

    user_prompt = build_user_prompt(question, course_context)


    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.2,
        max_tokens=600
    )


    # Plain prose, so there is no JSON to parse or fall back from.
    return response.choices[0].message.content.strip()
