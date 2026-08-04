from pydantic import BaseModel

class StudyPlanRequest(BaseModel):
    user_id: str
    course_id: str
    goal: str
    requesting_user_id: str

class StudyPlanResponse(BaseModel):
    success: bool
    study_plan: list[str]
    focus_topics: list[str] | None = None
    estimated_hours: float | None = None

