from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from agents import (
    call_study_agent,
    call_assessment_agent,
    call_faq_agent
)
from summarizer import build_overview, select_agents


# Agent slugs. These are what the frontend switches on, so they are also
# the values accepted in the request's "agent" field.
AGENT_STUDY = "study"
AGENT_QUIZ = "quiz"
AGENT_FAQ = "faq"



def classify(message: str) -> str:
    """
    Guess which agent should handle a free-form message.

    Note the ordering: study keywords win over quiz keywords, so
    "practice quiz for the final" lands on the Study Agent. Callers that
    already know which agent they want should pass it explicitly rather
    than phrase their way around this.
    """

    text = message.lower()


    if (
        "study" in text
        or "plan" in text
        or "exam" in text
        or "midterm" in text
        or "final" in text
    ):
        return AGENT_STUDY


    if (
        "quiz" in text
        or "test" in text
        or "practice" in text
    ):
        return AGENT_QUIZ


    return AGENT_FAQ



def route_request(
        message: str,
        user_id: str,
        course_id: str,
        agent: str | None = None,
        num_questions: int = 5
):

    # An explicit agent skips keyword matching entirely.
    chosen = agent or classify(message)


    if chosen == AGENT_STUDY:

        print("[ORCHESTRATOR] Routing → Study Agent")

        response = call_study_agent(
            user_id=user_id,
            course_id=course_id,
            goal=message
        )


    elif chosen == AGENT_QUIZ:

        print("[ORCHESTRATOR] Routing → Assessment Agent")

        response = call_assessment_agent(
            user_id=user_id,
            course_id=course_id,
            topic=message,
            num_questions=num_questions
        )


    else:

        print("[ORCHESTRATOR] Routing → FAQ Agent")

        response = call_faq_agent(
            question=message,
            course_id=course_id
        )


    return {
        "success": True,
        "agent": chosen,
        "response": response
    }



def _run_one(
        slug: str,
        message: str,
        user_id: str,
        course_id: str,
        num_questions: int
) -> dict:
    """
    Run a single agent, converting any failure into a result rather than an
    exception. One agent having no material must not sink the whole request.
    """

    try:

        if slug == AGENT_STUDY:
            response = call_study_agent(
                user_id=user_id,
                course_id=course_id,
                goal=message
            )

        elif slug == AGENT_QUIZ:
            response = call_assessment_agent(
                user_id=user_id,
                course_id=course_id,
                topic=message,
                num_questions=num_questions
            )

        else:
            response = call_faq_agent(
                question=message,
                course_id=course_id
            )

        return {
            "success": True,
            "response": response
        }


    except HTTPException as e:
        return {
            "success": False,
            "message": str(e.detail)
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }



def route_all(
        message: str,
        user_id: str,
        course_id: str,
        agents: list[str] | None = None,
        num_questions: int = 5
):
    """
    Fan a single message out to every relevant agent, then summarize.

    Used by the workspace UI, where one query fills several tabs at once.
    """

    selected = agents or select_agents(message)

    # select_agents returns [] if the model answered with something
    # unparseable; fall back to the keyword rules rather than doing nothing.
    if not selected:
        selected = [classify(message)]

    print("[ORCHESTRATOR] Fanning out to:", ", ".join(selected))


    # Each agent is a slow Azure round trip, so run them side by side.
    with ThreadPoolExecutor(max_workers=len(selected)) as pool:

        futures = {
            slug: pool.submit(
                _run_one,
                slug,
                message,
                user_id,
                course_id,
                num_questions
            )
            for slug in selected
        }

        results = {slug: f.result() for slug, f in futures.items()}


    overview = build_overview(message, results)


    return {
        "success": True,
        "query": message,
        "overview": overview,
        "selected_agents": selected,
        "agents": results
    }
