from fastapi import FastAPI, HTTPException 
from models import StudyPlanRequest, StudyPlanResponse
from agent import study_and_plan_agent

app = FastAPI(
    title = "Study Plan Generator API",
    version = "1.0.0"
)

@app.get("/health")
def read_health():
    return {"status": "healthy"}

@app.post("/study/plan", response_model=StudyPlanResponse)
def get_study_plan(study: StudyPlanRequest):

    try:
        result = study_and_plan_agent(
                        user_id = study.user_id,
                        course_id = study.course_id,
                        goal = study.goal,)
        
        return StudyPlanResponse(
            success=True,
            study_plan=result.get("study_plan", []),
            focus_topics=result.get("focus_topics", []),
            estimated_hours=result.get("estimated_hours", None)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))