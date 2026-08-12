from pydantic import BaseModel


class FAQRequest(BaseModel):
    question: str
    course_id: str


class FAQResponse(BaseModel):
    success: bool
    answer: str
