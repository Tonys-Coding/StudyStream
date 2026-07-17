from data import get_course_context

SYSTEM_PROMPT = """
You are a professional AI study assistant for a university course. 
Your job is to generate structured, actionable study plans based on a student's goal 
and the course context provided. 
Please provide a clear, structured plan that includes a 
step-by-step study plan, key focus areas,
estimated hours required, and any additional resources or tips.
            
You must return your response as a valid JSON object using EXACTLY this structure:
{
  "study_plan": ["step 1", "step 2", "step 3"],
  "focus_topics": ["topic 1", "topic 2"],
  "estimated_hours": 5.0
}

Rules:
- Return ONLY the JSON object. No extra text, no explanation, no markdown code.
- study_plan steps must be specific and actionable, not vague
- Order steps from foundational concepts to advanced application
- focus_topics should be 2-4 topics most relevant to the stated goal
- estimated_hours should be a realistic float value           
"""


def build_user_prompt(goal: str, course_context: dict) -> str: 
    """
    Constructs the user prompt for the AI model based on the
    user's goal and the course context. 
    """
    chunks = course_context.get("content_chunks", [])
    
    if chunks: 
      material_block = "\n\n---\n\n".join(chunks)
    else:
      material_block = "No specific course material was found for this course."

    return f"""Student goal: {goal} 

    Relevant course material:
    {material_block} 
    Generate a personalized study plan for this student based on the material above."""