# Temporary hard-coded course data
# This file can later be replaced with a database or RAG retrieval.


COURSE_DATA = {
    # Topics here mirror study-agent/sample.txt, the syllabus ingested into
    # Supabase under HIST301. Keep the two in sync, otherwise the quiz and
    # the study plan describe different courses.
    "HIST301": {
        "course_name": "Time Travel & Historical Paradoxes",
        "topics": [
            "Theoretical Time Dilation",
            "Temporal Mechanics and Paradoxes",
            "The Grandfather Paradox",
            "The Butterfly Effect",
            "Ethics of Historical Intervention",
            "Alternate Histories"
        ]
    },
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