import random
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import ModelOutputError, chat_json
from prompts import SYSTEM_PROMPT, build_user_prompt


def _resolve_answer(answer, choices: list[str]) -> str | None:
    """
    Finds which of the four choices the model meant, or None.

    The prompt asks for the answer to repeat a choice word for word, but
    models also reply with "b", "B)", or a different capitalisation. The
    quiz is only gradable if the answer matches a choice, so repair what can
    be repaired and reject the rest.
    """

    if isinstance(answer, int) and not isinstance(answer, bool):
        return choices[answer] if 0 <= answer < len(choices) else None

    if not isinstance(answer, str):
        return None

    answer = answer.strip()

    if answer in choices:
        return answer

    lowered = answer.lower()

    for choice in choices:
        if choice.lower() == lowered:
            return choice

    letter = re.fullmatch(r"([A-Da-d])[\).:]?", answer)

    if letter:
        return choices[ord(letter.group(1).upper()) - ord("A")]

    return None


def _clean_question(raw) -> dict | None:
    """One well-formed question, or None if it cannot be made one."""

    if not isinstance(raw, dict):
        return None

    text = raw.get("question")
    choices = raw.get("choices")

    if not isinstance(text, str) or not text.strip():
        return None

    if not isinstance(choices, list):
        return None

    unique: list[str] = []

    for c in choices:
        if isinstance(c, str) and c.strip() and c.strip() not in unique:
            unique.append(c.strip())

    if len(unique) != 4:
        return None

    answer = _resolve_answer(raw.get("answer"), unique)

    if answer is None:
        return None

    # Models like to put the right answer first or second. Shuffle so the
    # position tells the student nothing; the answer is matched by text.
    random.shuffle(unique)

    explanation = raw.get("explanation")

    return {
        "question": text.strip(),
        "choices": unique,
        "answer": answer,
        "explanation": explanation.strip() if isinstance(explanation, str) else ""
    }


def _validator(num_questions: int):

    def validate(parsed) -> list[dict]:

        raw = parsed.get("questions") if isinstance(parsed, dict) else parsed

        if not isinstance(raw, list):
            raise ModelOutputError("The quiz came back in the wrong shape.")

        questions = [q for q in map(_clean_question, raw) if q]

        if not questions:
            raise ModelOutputError("The quiz had no usable questions.")

        return questions[:num_questions]

    return validate


def assessment_agent(
    course_id: str,
    topic: str,
    num_questions: int,
    course_context: dict
) -> list[dict]:
    """
    Writes a quiz from the retrieved course material.

    Every question returned has exactly four distinct choices and an answer
    that is one of them. Questions that do not pass are dropped, and if none
    pass the call raises instead of returning an ungradable quiz.
    """

    return chat_json(
        SYSTEM_PROMPT,
        build_user_prompt(topic, course_context, num_questions),
        validate=_validator(num_questions),
        temperature=0.4,
        max_tokens=min(4000, 300 * num_questions + 300)
    )
