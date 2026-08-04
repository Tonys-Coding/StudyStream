from fastapi import FastAPI
from pydantic import BaseModel

from router import route_request

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    user_id: str
    course_id: str


@app.post("/chat")
async def chat(request: ChatRequest):

    result = await route_request(
        message=request.message,
        user_id=request.user_id,
        course_id=request.course_id
    )

    return result



# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel

# from router import route_request


# app = FastAPI(
#     title="AI Classroom Assistant Orchestrator",
#     version="1.0.0"
# )


# class ChatRequest(BaseModel):
#     message: str
#     user_id: str
#     course_id: str



# @app.get("/health")
# def health():
#     return {
#         "status": "healthy",
#         "service": "orchestrator"
#     }



# @app.post("/chat")
# def chat(request: ChatRequest):

#     print("\n[ORCHESTRATOR] Received message:")
#     print(request.message)


#     try:

#         result = route_request(
#             message=request.message,
#             user_id=request.user_id,
#             course_id=request.course_id
#         )


#         return result


#     except Exception as e:

#         print("[ORCHESTRATOR ERROR]", str(e))

#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )