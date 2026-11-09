from pydantic import BaseModel


class FAQRequest(BaseModel):
    question: str
    course_id: str

    # Decides which private uploads the answer may draw on.
    user_id: str | None = None


class FAQResponse(BaseModel):
    success: bool
    answer: str

    # Files the answer drew on, most relevant first.
    sources: list[str] = []
