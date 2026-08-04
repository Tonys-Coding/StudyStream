# auth_stub.py
def get_current_user() -> dict:
    return {"id": "00000000-0000-0000-0000-000000000001", "role": "student"}

def check_enrollment(user_id: str, course_id: str) -> bool:
    return True