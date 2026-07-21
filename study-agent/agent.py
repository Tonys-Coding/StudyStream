import os
import json
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv
from data import get_course_context #Importing file 
from prompts import SYSTEM_PROMPT, build_user_prompt #Importing file

#Loading .env from the same directory as this file
project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

print("Loaded endpoint:", os.getenv("AZURE_OPENAI_ENDPOINT"))
print("Loaded deployment:", os.getenv("AZURE_DEPLOYMENT_NAME"))
print("API key exists:", os.getenv("AZURE_OPENAI_API_KEY") is not None)

#Azure OpenAI client initalization
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)

#Deployment from .env
DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")

if not os.getenv("AZURE_OPENAI_ENDPOINT"):
    raise ValueError("Missing AZURE_OPENAI_ENDPOINT in .env")

if not os.getenv("AZURE_OPENAI_API_KEY"):
    raise ValueError("Missing AZURE_OPENAI_API_KEY in .env")

if not DEPLOYMENT_NAME:
    raise ValueError("Missing AZURE_DEPLOYMENT_NAME in .env")

#Agent Initialization
def study_and_plan_agent(user_id: str, course_id: str, goal:str) -> dict:
    """
    This is the core agent logic. 
    Takes a goal + context, calls the Azure OpenAI API, and returns a structured study plan/guide
    """

    #Get course context (hardcoded for now)
    course_context = get_course_context(course_id)

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
            "focus_areas": [],
            "estimated_hours": None,
        }
    
    return parsed_response