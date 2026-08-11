import os
import json
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT, build_user_prompt #Importing file

#Loading .env from the same directory as this file
#script_dir = Path(__file__).parent
#load_dotenv(script_dir / ".env")

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


#Agent Initialization
def study_and_plan_agent(
        user_id: str,
        course_id: str,
        goal: str,
        course_context: dict
) -> dict:
    """
    This is the core agent logic.
    Takes a goal + context, calls the Azure OpenAI API, and returns a structured study plan/guide

    The caller retrieves the context and passes it in. Fetching it here as
    well would embed the goal a second time and re-run the vector search,
    doubling the latency and the embedding spend on every request.
    """

    #Build the user prompt
    user_prompt = build_user_prompt(goal, course_context)

    #Call Azure OpenAI -> Chat Completions
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=1000
    )

    #Extract text
    raw_text = response.choices[0].message.content

    #Parse JSON
    try:
        parsed_response = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed_response = {
            "study_plan": [raw_text],
            "focus_topics": [],
            "estimated_hours": None,
        }
    
    return parsed_response