from fastapi import FastAPI, HTTPException 
from models import StudyPlanRequest, StudyPlanResponse
from agent import study_and_plan_agent
from data import get_course_context, course_has_content

#For extensive exception type handling
from openai import AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError, APIError

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
        if not course_has_content(study.course_id):
            raise HTTPException(status_code=404, detail=f"No content found for course_id: {study.course_id}")

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