import os

import requests

from data import FAQ_ENTRIES, build_context_snippet, find_answer, top_matching_entries
from prompts import SYSTEM_INSTRUCTIONS, build_user_message

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_RESPONSES_URL = os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses")
OPENAI_TIMEOUT_S = float(os.getenv("OPENAI_TIMEOUT_S", "15"))


def answer_with_openai(question: str, context: str) -> str | None:
    if not OPENAI_API_KEY:
        return None

    # Uses OpenAI Responses API over plain HTTP to avoid extra dependencies.
    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {
                "role": "user",
                "content": build_user_message(question, context),
            },
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            OPENAI_RESPONSES_URL,
            headers=headers,
            json=payload,
            timeout=OPENAI_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print("[FAQ AGENT] OpenAI request failed:", repr(e))
        return None

    # Best-effort parse: handle common Responses shapes.
    try:
        if isinstance(data, dict) and isinstance(data.get("output_text"), str) and data["output_text"].strip():
            return data["output_text"].strip()
        output = data.get("output", [])
        if isinstance(output, list):
            chunks: list[str] = []
            for item in output:
                for content in item.get("content", []) if isinstance(item, dict) else []:
                    if isinstance(content, dict) and content.get("type") in ("output_text", "text"):
                        text = content.get("text", "")
                        if isinstance(text, str) and text.strip():
                            chunks.append(text.strip())
            if chunks:
                return "\n".join(chunks).strip()
    except Exception as e:
        print("[FAQ AGENT] OpenAI response parse failed:", repr(e))

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

    ai_answer = answer_with_openai(query, context)
    answer = ai_answer if ai_answer is not None else find_answer(query, FAQ_ENTRIES)

    return {
        "user_id": user_id,
        "course_id": course_id,
        "query": query,
        "answer": answer,
    }
