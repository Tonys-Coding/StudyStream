import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)

DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")


VALID_AGENTS = ("study", "quiz", "faq")


SELECT_SYSTEM_PROMPT = """
You decide which specialist agents should handle a student's message.

The agents are:
- "study": builds a step-by-step study plan, focus topics, and an hour
  estimate. Relevant when the student wants to prepare, revise, schedule
  work, or get ready for something.
- "quiz": writes multiple-choice practice questions. Relevant when the
  student wants to test themselves, practice, or rehearse recall.
- "faq": answers factual questions about the course itself - policies,
  grading, deadlines, office hours, required readings, what is covered.

Return ONLY a JSON array of the agent names that would genuinely help,
for example: ["study","faq"]

Rules:
- Pick every agent that adds real value to this message.
- Pick at least one agent.
- When the student is preparing broadly - for an exam, a project, or the
  course as a whole - more than one agent usually helps: a plan to work
  through, questions to practise against, and the course facts that frame
  them. Choose all of those.
- When the student asks a narrow factual question that has a single direct
  answer, such as a deadline, a grade weight, or an office hour, choose only
  "faq". Do not attach a study plan or a quiz to it.
- Return only the JSON array. No explanation, no markdown.
"""


OVERVIEW_SYSTEM_PROMPT = """
You write a short overview for a student, summarizing what the specialist
assistants just produced for them.

Rules:
- 2 to 4 sentences of plain prose. No markdown, no bullet points, no headings.
- Summarize the substance of what was produced, not the process. Do not say
  "the agents returned" or refer to agents, tabs, or systems.
- Mention the concrete highlights: how many study steps, how many practice
  questions, the key focus areas, the direct answer to their question.
- If something could not be produced, mention it briefly and plainly.
- Address the student directly as "you".
"""


def select_agents(message: str) -> list[str]:
    """
    Ask the model which agents are relevant to this message.

    Returns a list of agent slugs. Raises nothing - callers get a usable
    list even if the model misbehaves, since an empty or malformed answer
    is filtered out and handled by the caller's fallback.
    """

    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": SELECT_SYSTEM_PROMPT},
            {"role": "user", "content": message}
        ],
        temperature=0,
        max_tokens=60
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    # Keep declared order (study, quiz, faq) so the UI tab order is stable
    chosen = {a for a in parsed if a in VALID_AGENTS}

    return [a for a in VALID_AGENTS if a in chosen]


def build_overview(message: str, results: dict) -> str:
    """
    Write the Overview text from whatever the agents produced.

    `results` maps agent slug -> {"success": bool, ...}.
    """

    succeeded = {
        slug: r.get("response")
        for slug, r in results.items()
        if r.get("success")
    }

    failed = {
        slug: r.get("message")
        for slug, r in results.items()
        if not r.get("success")
    }

    # Nothing to summarize - don't spend a model call saying so.
    if not succeeded:
        if failed:
            return (
                "Nothing could be generated for this request. "
                + " ".join(str(m) for m in failed.values())
            )
        return "Nothing was generated for this request."

    user_prompt = f"""
Student's request:
{message}

What was produced (JSON):
{json.dumps(succeeded, indent=2)[:6000]}
"""

    if failed:
        user_prompt += f"""
What could not be produced:
{json.dumps(failed, indent=2)[:1000]}
"""

    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": OVERVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=300
    )

    return response.choices[0].message.content.strip()
