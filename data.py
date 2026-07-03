
COURSE_DATA = {
    "CS3354": {
        "name": "Software Engineering",
        "topics": [
            "Requirements Engineering",
            "System Architecture",
            "Design Patterns"
        ],
        "upcoming_exams": [
            {
                "name": "Midterm Exam",
                "topics": ["Requirements Engineering", "System Architecture"]
            },
            {
                "name": "Final Exam",
                "topics": ["Design Patterns", "System Architecture"]
            }
        ],
        "assignments": [
            {
                "name": "First Homework Assignment",
                "description": "Introductory work covering each topic"
            },
            {
                "name": "Midterm Assignment",
                "description": "Intermediate level questions about each topic"
            }
        ]
    }
}

def get_course_context(course_id: str):
    return COURSE_DATA.get(course_id, {})


# Verification Test
if __name__ == "__main__":
    print(get_course_context("CS3354"))
    print(get_course_context("FAKE101"))

