from pydantic import BaseModel, Field


class QuizRequest(BaseModel):
    user_id: str | None = None
    course_id: str
    topic: str

    # Bounded so one request cannot ask the model for an enormous quiz.
    num_questions: int = Field(default=5, ge=1, le=20)


class QuizQuestion(BaseModel):
    question: str
    choices: list[str]
    answer: str

    # Why the answer is right, shown to the student after they pick.
    explanation: str = ""


class QuizResponse(BaseModel):
    success: bool
    questions: list[QuizQuestion]

    # Files the questions were written from, most relevant first.
    sources: list[str] = []
