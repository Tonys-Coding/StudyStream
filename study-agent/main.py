'''

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class StudyRequest(BaseModel):
    topic: str
    days_until_exam: int = 7


@app.post("/study_plan")
def study_plan(request: StudyRequest):

    print("[STUDY AGENT] Creating plan for:", request.topic)

    plan = [
        f"Day 1-2: Basics of {request.topic}",
        f"Day 3-4: Practice problems",
        f"Day 5: Quiz yourself",
        f"Day 6: Review mistakes",
        f"Day 7: Final review"
    ]

    print("[STUDY AGENT] Plan ready")

    return {
        "topic": request.topic,
        "plan": plan
    }
    
    '''
    
from fastapi import FastAPI, HTTPException 
from models import StudyPlanRequest, StudyPlanResponse
from agent import study_and_plan_agent
from data import get_course_context

#For extensive exception type handling
from openai import AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError, APIError

app = FastAPI(
    title = "Study Plan Generator API",
    version = "1.0.0"
)

@app.get("/health")
def read_health():
    return {"status": "healthy"}

@app.post("/study_plan", response_model=StudyPlanResponse)
def get_study_plan(study: StudyPlanRequest):

    try:
        course_context = get_course_context(study.course_id)
        goal = study.goal.strip() if study.goal else None

        if not course_context:
            raise HTTPException(status_code=404, detail=f"Course context not found for course_id: {study.course_id}")

        if not goal:
            raise HTTPException(status_code=400, detail="Missing required field: goal is required.")

        result = study_and_plan_agent(
                        user_id = study.user_id,
                        course_id = study.course_id,
                        goal = goal,)
        
        
        return StudyPlanResponse(
            success=True,
            study_plan=result.get("study_plan", []),
            focus_topics=result.get("focus_topics", []),
            estimated_hours=result.get("estimated_hours", None)
        )
    
    except HTTPException:
        raise 
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {str(e)}")
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")
    except APITimeoutError as e:
        raise HTTPException(status_code=504, detail=f"API timeout: {str(e)}")
    except APIConnectionError as e:
        raise HTTPException(status_code=503, detail=f"API connection error: {str(e)}")
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))