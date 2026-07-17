# Temporary hard-coded course data
# This file can later be replaced with a database or RAG retrieval.


COURSE_DATA = {
    "CS3354": {
        "course_name": "Software Engineering",
        "topics": [
            "Requirements Engineering",
            "Software Design",
            "System Architecture",
            "Testing",
            "Agile Development"
        ]
    },
    "CS2336": {
        "course_name": "Computer Science II",
        "topics": [
            "Classes and Objects",
            "Inheritance",
            "Polymorphism",
            "Templates",
            "Linked Lists",
            "Trees"
        ]
    }
}


def get_course_context(course_id: str):
    """
    Returns course information for the requested course.
    Returns None if the course does not exist.
    """
    return COURSE_DATA.get(course_id)