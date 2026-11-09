import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import chat_text
from prompts import SYSTEM_PROMPT, build_user_prompt


def faq_agent(question: str, course_context: dict) -> str:
    """
    Answers a course question from retrieved material.

    Takes the context as an argument rather than fetching it, so the caller
    can check for empty retrieval first and we only embed the question once.
    Plain prose, so there is no JSON to parse or fall back from.
    """

    return chat_text(
        SYSTEM_PROMPT,
        build_user_prompt(question, course_context),
        temperature=0.2,
        max_tokens=600
    )
