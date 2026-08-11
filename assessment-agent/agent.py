import os
import json
from pathlib import Path

from openai import AzureOpenAI
from dotenv import load_dotenv

from data import get_course_context
from prompts import SYSTEM_PROMPT, build_user_prompt


# Load .env file
# For now, assuming .env is inside the AI-Classroom-Assistant root folder
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)


# Azure deployment name
DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")


def assessment_agent(
    user_id: str,
    course_id: str,
    topic: str,
    num_questions: int
) -> dict:
    """
    Main Assessment Agent logic.

    Takes:
        - user_id
        - course_id
        - topic
        - number of questions

    Returns:
        Structured quiz questions.
    """

    # Get course information
    course_context = get_course_context(course_id)

    if not course_context:
        return {
            "questions": [],
            "error": f"Course not found: {course_id}"
        }


    # Build prompt
    user_prompt = build_user_prompt(
        topic,
        course_context,
        num_questions
    )


    # Call Azure OpenAI
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3,
        max_tokens=1500
    )


    # Extract response text
    raw_text = response.choices[0].message.content


    # Convert JSON string to Python object
    try:
        parsed_response = json.loads(raw_text)

    except json.JSONDecodeError:

        parsed_response = {
            "questions": [
                {
                    "question": raw_text,
                    "choices": [],
                    "answer": ""
                }
            ]
        }


    return parsed_response