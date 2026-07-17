from pydantic import BaseModel
from typing import List


class QuizRequest(BaseModel):
    user_id: str
    course_id: str
    topic: str
    num_questions: int = 5


class QuizQuestion(BaseModel):
    question: str
    choices: List[str]
    answer: str


class QuizResponse(BaseModel):
    success: bool
    questions: List[QuizQuestion]