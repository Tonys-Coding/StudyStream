import json
from pathlib import Path

from prompts import FALLBACK_ANSWER

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


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


FAQ_ENTRIES = load_faq_entries()


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
