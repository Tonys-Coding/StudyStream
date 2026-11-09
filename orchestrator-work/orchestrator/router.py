from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from agents import (
    call_study_agent,
    call_assessment_agent,
    call_faq_agent
)
from summarizer import build_overview, fallback_overview, select_agents


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
            course_id=course_id,
            user_id=user_id
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
                course_id=course_id,
                user_id=user_id
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

    selected = agents

    if not selected:

        # Choosing agents is itself a model call. If Azure is down or slow,
        # the keyword rules still give a usable answer.
        try:
            selected = select_agents(message)
        except Exception as e:
            print("[ORCHESTRATOR] Agent selection failed:", type(e).__name__, e)
            selected = []

    # Also covers select_agents returning [] on an unparseable answer.
    if not selected:
        selected = [classify(message)]

    # The Answer tab is the one every question deserves: "summarise my paper"
    # or "explain this in simple words" is not a policy question, so keyword or
    # model selection tends to skip it. Always answer, unless the caller named
    # the agents themselves.
    if not agents and "faq" not in selected:
        selected = [*selected, "faq"]

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


    # The agents' work is done. A failed summary must not throw it away.
    try:
        overview = build_overview(message, results)
    except Exception as e:
        print("[ORCHESTRATOR] Overview failed:", type(e).__name__, e)
        overview = fallback_overview(results)


    return {
        "success": True,
        "query": message,
        "overview": overview,
        "selected_agents": selected,
        "agents": results
    }
