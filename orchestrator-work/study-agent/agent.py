import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import ModelOutputError, chat_json
from prompts import SYSTEM_PROMPT, build_user_prompt


def _validate(parsed) -> dict:
    """
    Checks the model's JSON has the shape the UI draws, and tidies it.

    Raises ModelOutputError instead of passing a malformed plan through, so
    the student never sees raw JSON as "step 1".
    """

    if not isinstance(parsed, dict):
        raise ModelOutputError("The study plan came back in the wrong shape.")

    steps = parsed.get("study_plan")

    if not isinstance(steps, list):
        raise ModelOutputError("The study plan had no steps.")

    steps = [s.strip() for s in steps if isinstance(s, str) and s.strip()]

    if not steps:
        raise ModelOutputError("The study plan had no steps.")

    topics = parsed.get("focus_topics")

    if isinstance(topics, list):
        topics = [t.strip() for t in topics if isinstance(t, str) and t.strip()]
    else:
        topics = []

    hours = parsed.get("estimated_hours")

    if isinstance(hours, bool) or not isinstance(hours, (int, float)) or hours < 0:
        hours = None

    return {
        "study_plan": steps,
        "focus_topics": topics,
        "estimated_hours": float(hours) if hours is not None else None
    }


def study_and_plan_agent(
        user_id: str,
        course_id: str,
        goal: str,
        course_context: dict
) -> dict:
    """
    Takes a goal and the retrieved course material, asks the model for a
    structured plan, and returns it validated.

    The caller retrieves the context and passes it in, so the goal is
    embedded once per request rather than twice.
    """

    return chat_json(
        SYSTEM_PROMPT,
        build_user_prompt(goal, course_context),
        validate=_validate,
        temperature=0.3,
        max_tokens=1200
    )
