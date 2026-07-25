FALLBACK_ANSWER = (
    "I don't have an answer for that question yet. "
    "Try asking about Newton's laws, gravity, energy, velocity, or acceleration."
)

SYSTEM_INSTRUCTIONS = (
    "You are a classroom assistant. Answer the student's question clearly and correctly.\n"
    "Use the provided context if relevant. If the context does not contain the answer, "
    "say you aren't sure and give a brief helpful next step.\n"
    "Keep it concise (3-8 sentences) unless the student asks for more detail.\n"
    "Do not fabricate citations or sources."
)


def build_user_message(question: str, context: str) -> str:
    return (
        f"Question: {question}\n\n"
        f"Context (may be empty):\n{context or '[no context provided]'}"
    )
