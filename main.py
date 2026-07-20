import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI()

DOCS_DIR = PROJECT_ROOT / "docs"
FALLBACK_ANSWER = (
    "I don't have an answer for that question yet. "
    "Try asking about Newton's laws, gravity, energy, velocity, or acceleration."
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_RESPONSES_URL = os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses")
OPENAI_TIMEOUT_S = float(os.getenv("OPENAI_TIMEOUT_S", "15"))


class FAQRequest(BaseModel):
    """Standard request object used with the orchestrator.

    Preferred shape:
      {"user_id": "...", "course_id": "...", "query": "..."}

    Legacy orchestrator compatibility:
      {"question": "..."}  # mapped to query when query is omitted
    """

    user_id: str | None = Field(default=None, description="Unique student identifier")
    course_id: str | None = Field(default=None, description="Course identifier")
    query: str | None = Field(default=None, description="Student request")
    question: str | None = Field(
        default=None,
        description="Legacy field accepted only for older orchestrator payloads",
        exclude=True,
    )

    @model_validator(mode="after")
    def require_query_or_legacy_question(self) -> "FAQRequest":
        if self.query and self.query.strip():
            self.query = self.query.strip()
            return self
        if self.question and self.question.strip():
            self.query = self.question.strip()
            return self
        raise ValueError("Field 'query' is required (or legacy 'question').")

    @property
    def student_query(self) -> str:
        return self.query or ""


def load_faq_entries() -> list[dict]:
    entries = []
    if not DOCS_DIR.exists():
        return entries

    for file_path in sorted(DOCS_DIR.glob("*.json")):
        with file_path.open(encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                entries.extend(data)

    return entries


def find_answer(question: str, entries: list[dict]) -> str:
    normalized_question = question.lower()
    best_match = None
    best_score = 0

    for entry in entries:
        score = 0
        for keyword in entry.get("keywords", []):
            if keyword.lower() in normalized_question:
                score += len(keyword)

        if score > best_score:
            best_score = score
            best_match = entry

    if best_match:
        return best_match["answer"]

    return FALLBACK_ANSWER


FAQ_ENTRIES = load_faq_entries()


def top_matching_entries(question: str, entries: list[dict], limit: int = 4) -> list[dict]:
    q = question.lower()
    scored: list[tuple[int, dict]] = []

    for entry in entries:
        score = 0
        for keyword in entry.get("keywords", []):
            kw = str(keyword).lower()
            if kw and kw in q:
                score += len(kw)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [entry for _, entry in scored[:limit]]


def build_context_snippet(matched: list[dict]) -> str:
    if not matched:
        return ""
    parts: list[str] = []
    for i, entry in enumerate(matched, start=1):
        keywords = ", ".join(entry.get("keywords", [])[:6])
        answer = entry.get("answer", "")
        parts.append(f"[Doc {i}] keywords: {keywords}\n[Doc {i}] answer: {answer}")
    return "\n\n".join(parts).strip()


def answer_with_openai(question: str, context: str) -> str | None:
    if not OPENAI_API_KEY:
        return None

    instructions = (
        "You are a classroom assistant. Answer the student's question clearly and correctly.\n"
        "Use the provided context if relevant. If the context does not contain the answer, say you aren't sure and give a brief helpful next step.\n"
        "Keep it concise (3-8 sentences) unless the student asks for more detail.\n"
        "Do not fabricate citations or sources."
    )

    # Uses OpenAI Responses API over plain HTTP to avoid extra dependencies.
    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "system", "content": instructions},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Context (may be empty):\n{context or '[no context provided]'}"
                ),
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

    matched = top_matching_entries(query, FAQ_ENTRIES)
    context = build_context_snippet(matched)
    if request.course_id:
        context = (
            f"Course: {request.course_id}\n"
            f"Student: {request.user_id or 'unknown'}\n\n"
            f"{context}"
        ).strip()

    ai_answer = answer_with_openai(query, context)
    answer = ai_answer if ai_answer is not None else find_answer(query, FAQ_ENTRIES)

    print("[FAQ AGENT] Sending response")

    return {
        "user_id": request.user_id,
        "course_id": request.course_id,
        "query": query,
        "answer": answer,
    }
