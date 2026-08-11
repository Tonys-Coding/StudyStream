from pydantic import BaseModel, Field, model_validator


class FAQRequest(BaseModel):
    """Standard request object used with the orchestrator.

    Preferred shape:
      {"user_id": "...", "course_id": "...", "query": "..."}

    Legacy orchestrator compatibility:
      {"question": "..."}  # mapped to query when query is omitted
    """

    user_id: str | None = Field(default=None, description="Unique student identifier")
    course_id: str | None = Field(default=None, description="Course identifier")
    query: str | None = Field(default=None, description="Student request")
    question: str | None = Field(
        default=None,
        description="Legacy field accepted only for older orchestrator payloads",
        exclude=True,
    )

    @model_validator(mode="after")
    def require_query_or_legacy_question(self) -> "FAQRequest":
        if self.query and self.query.strip():
            self.query = self.query.strip()
            return self
        if self.question and self.question.strip():
            self.query = self.question.strip()
            return self
        raise ValueError("Field 'query' is required (or legacy 'question').")

    @property
    def student_query(self) -> str:
        return self.query or ""
