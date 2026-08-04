from fastapi import Depends, FastAPI, HTTPException, UploadFile 
from models import StudyPlanRequest, StudyPlanResponse
from agent import study_and_plan_agent
from data import get_course_context, course_has_content, get_visible_materials, ingest_file, save_upload_temporarily
from auth_stub import get_current_user, check_enrollment

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
                        requesting_user_id = study.requesting_user_id,
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
    

@app.post("/materials/upload")
def upload_material(file: UploadFile, course_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("teacher", "student"):
        raise HTTPException(status_code=403, detail="Only teachers and students can upload materials.")
    
    temp_path = save_upload_temporarily(file)

    if current_user["role"] == "teacher":
        visibility = "class"
    else:
        visibility = "private"
        
    ingest_file(temp_path, 
                uploaded_by = current_user["id"], 
                course_id=course_id, 
                visibility=visibility, 
                tag="uploaded")

    return {"success": True}

@app.get("/materials/{course_id}")
def get_materials(course_id: str, requesting_user_id: str, current_user: dict = Depends(get_current_user)):
    return get_visible_materials(course_id, current_user["id"])