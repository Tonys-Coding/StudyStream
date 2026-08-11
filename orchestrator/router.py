from agents import (
    call_study_agent,
    call_assessment_agent,
    call_faq_agent
)



def route_request(
        message: str,
        user_id: str,
        course_id: str
):

    text = message.lower()


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


        result = call_study_agent(
            user_id=user_id,
            course_id=course_id,
            goal=message
        )


        return {
            "agent": "Study Agent",
            "response": result
        }



    # -------------------------
    # Assessment Agent
    # -------------------------
    elif (
        "quiz" in text
        or "test" in text
        or "practice" in text
    ):

        print("[ORCHESTRATOR] Routing → Assessment Agent")


        result = call_assessment_agent(
            user_id=user_id,
            course_id=course_id,
            topic=message,
            num_questions=5
        )


        return {
            "agent": "Assessment Agent",
            "response": result
        }


    # -------------------------
    # FAQ Agent
    # -------------------------
    else:

        print("[ORCHESTRATOR] Routing → FAQ Agent")


        result = call_faq_agent(
            question=message
        )


        return {
            "agent": "FAQ Agent",
            "response": result
        }