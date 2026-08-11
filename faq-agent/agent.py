import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

from data import FAQ_ENTRIES, build_context_snippet, find_answer, top_matching_entries
from prompts import SYSTEM_INSTRUCTIONS, build_user_message

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
)

DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")


def answer_with_azure(question: str, context: str) -> str | None:
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": build_user_message(question, context)},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as error:
        print("[FAQ AGENT] Azure OpenAI request failed:", repr(error))
        return None


def answer_faq(
    query: str,
    *,
    user_id: str | None = None,
    course_id: str | None = None,
) -> dict:
    matched = top_matching_entries(query, FAQ_ENTRIES)
    context = build_context_snippet(matched)

    if course_id:
        context = (
            f"Course: {course_id}\n"
            f"Student: {user_id or 'unknown'}\n\n"
            f"{context}"
        ).strip()

    ai_answer = answer_with_azure(query, context)
    answer = ai_answer if ai_answer else find_answer(query, FAQ_ENTRIES)

    return {
        "user_id": user_id,
        "course_id": course_id,
        "query": query,
        "answer": answer,
    }