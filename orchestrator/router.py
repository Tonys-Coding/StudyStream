import asyncio

from agents import (
    call_study_agent,
    call_assessment_agent,
    call_faq_agent
)


async def route_request(
        message: str,
        user_id: str,
        course_id: str
):

    text = message.lower()

    tasks = {}


    # -------------------------
    # Study Agent
    # -------------------------
    if (
        "study" in text
        or "plan" in text
        or "exam" in text
        or "midterm" in text
        or "final" in text
    ):

        print("[ORCHESTRATOR] Routing → Study Agent")

        tasks["study"] = call_study_agent(
            user_id=user_id,
            course_id=course_id,
            goal=message
        )


    # -------------------------
    # Assessment Agent
    # -------------------------
    if (
        "quiz" in text
        or "test" in text
        or "practice" in text
    ):

        print("[ORCHESTRATOR] Routing → Assessment Agent")

        tasks["assessment"] = call_assessment_agent(
            user_id=user_id,
            course_id=course_id,
            topic=message,
            num_questions=5
        )


    # -------------------------
    # FAQ Agent
    # -------------------------
    if (
        "what" in text
        or "how" in text
        or "why" in text
        or "when" in text
        or "where" in text
        or "explain" in text
    ):

        print("[ORCHESTRATOR] Routing → FAQ Agent")

        tasks["faq"] = call_faq_agent(
            question=message
        )


    # Default
    if not tasks:

        print("[ORCHESTRATOR] No agent matched → FAQ")

        tasks["faq"] = call_faq_agent(
            question=message
        )


    # -------------------------
    # PARALLEL EXECUTION
    # -------------------------

    keys = list(tasks.keys())

    values = await asyncio.gather(
        *tasks.values()
    )


    results = {}

    for key, value in zip(keys, values):
        results[key] = value


    return results

    # # -------------------------
    # # Study Agent
    # # -------------------------
    # if (
    #     "study" in text
    #     or "plan" in text
    #     or "exam" in text
    #     or "midterm" in text
    #     or "final" in text
    # ):

    #     print("[ORCHESTRATOR] Routing → Study Agent")


    #     result = call_study_agent(
    #         user_id=user_id,
    #         course_id=course_id,
    #         goal=message
    #     )


    #     return {
    #         "agent": "Study Agent",
    #         "response": result
    #     }



    # # -------------------------
    # # Assessment Agent
    # # -------------------------
    # elif (
    #     "quiz" in text
    #     or "test" in text
    #     or "practice" in text
    # ):

    #     print("[ORCHESTRATOR] Routing → Assessment Agent")


    #     result = call_assessment_agent(
    #         user_id=user_id,
    #         course_id=course_id,
    #         topic=message,
    #         num_questions=5
    #     )


    #     return {
    #         "agent": "Assessment Agent",
    #         "response": result
    #     }


    # # -------------------------
    # # FAQ Agent
    # # -------------------------
    # else:

    #     print("[ORCHESTRATOR] Routing → FAQ Agent")


    #     result = call_faq_agent(
    #         question=message
    #     )


    #     return {
    #         "agent": "FAQ Agent",
    #         "response": result
    #     }