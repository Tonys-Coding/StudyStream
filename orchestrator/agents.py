import requests


# Agent URLs

STUDY_AGENT_URL = "http://localhost:8003/study_plan"

ASSESSMENT_AGENT_URL = "http://localhost:8002/generate_quiz"

FAQ_AGENT_URL = "http://localhost:8000/faq"



# -------------------------
# Study Agent
# -------------------------

def call_study_agent(
        user_id: str,
        course_id: str,
        goal: str
):

    response = requests.post(
        STUDY_AGENT_URL,
        json={
            "user_id": user_id,
            "course_id": course_id,
            "goal": goal
        },
        timeout=60
    )


    response.raise_for_status()

    return response.json()



# -------------------------
# Assessment Agent
# -------------------------

def call_assessment_agent(
        user_id: str,
    	course_id: str,
    	topic: str,
   		num_questions: int = 5
):

    response = requests.post(
        ASSESSMENT_AGENT_URL,
        json={
       		"user_id": user_id,
        	"course_id": course_id,
        	"topic": topic,
        	"num_questions": num_questions
        },
        timeout=60
    )


    response.raise_for_status()

    return response.json()



# -------------------------
# FAQ Agent
# -------------------------

def call_faq_agent(question: str):

    response = requests.post(
        FAQ_AGENT_URL,
        json={
            "question": question
        },
        timeout=60
    )


    response.raise_for_status()

    return response.json()