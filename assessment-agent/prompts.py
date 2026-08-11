SYSTEM_PROMPT = """
You are an AI Assessment Assistant for a university classroom.

Your job is to generate high-quality multiple-choice quiz questions based on
the student's course information and requested topic.

Always return ONLY valid JSON.

The JSON format must be:

{
    "questions": [
        {
            "question": "...",
            "choices": [
                "...",
                "...",
                "...",
                "..."
            ],
            "answer": "..."
        }
    ]
}

Rules:
- Generate the requested number of questions.
- Each question must have exactly four choices.
- Only one choice should be correct.
- The answer must exactly match one of the choices.
- Do not include explanations.
- Do not include markdown.
- Do not include any text outside the JSON.
"""


def build_user_prompt(topic: str,
                      course_context: dict,
                      num_questions: int) -> str:
    """
    Builds the user prompt sent to Azure OpenAI.
    """

    return f"""
Course Information

Course Name:
{course_context.get("course_name")}

Available Topics:
{", ".join(course_context.get("topics", []))}

Student Request:
Generate {num_questions} multiple-choice quiz questions about:

"{topic}"

Return ONLY valid JSON.
"""