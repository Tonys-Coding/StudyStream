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
    },

    "HIST2301": {
        "name": "World History Since 1500",
        "topics": [
            "The Age of Exploration",
            "The Industrial Revolution",
            "The Cold War Era"
        ],
        "upcoming_exams": [
            {
                "name": "Midterm Exam",
                "topics": ["The Age of Exploration", "The Industrial Revolution"]
            },
            {
                "name": "Final Exam",
                "topics": ["The Cold War Era", "The Industrial Revolution"]
            }
        ],
        "assignments": [
            {
                "name": "Primary Source Analysis",
                "description": "Analyze a primary source document from the Age of Exploration"
            },
            {
                "name": "Research Essay",
                "description": "5-page essay on causes and effects of the Industrial Revolution"
            }
        ]
    },

    "BIOL1441": {
        "name": "Introduction to Cell Biology",
        "topics": [
            "Cell Structure and Function",
            "Cellular Respiration",
            "DNA Replication and Protein Synthesis"
        ],
        "upcoming_exams": [
            {
                "name": "Midterm Exam",
                "topics": ["Cell Structure and Function", "Cellular Respiration"]
            },
            {
                "name": "Final Exam",
                "topics": ["DNA Replication and Protein Synthesis", "Cellular Respiration"]
            }
        ],
        "assignments": [
            {
                "name": "Lab Report: Microscopy",
                "description": "Identify and describe cell organelles observed under a microscope"
            },
            {
                "name": "Cellular Respiration Worksheet",
                "description": "Diagram and explain the stages of cellular respiration"
            }
        ]
    },

    "FIN3320": {
        "name": "Principles of Corporate Finance",
        "topics": [
            "Time Value of Money",
            "Risk and Return",
            "Capital Budgeting"
        ],
        "upcoming_exams": [
            {
                "name": "Midterm Exam",
                "topics": ["Time Value of Money", "Risk and Return"]
            },
            {
                "name": "Final Exam",
                "topics": ["Capital Budgeting", "Risk and Return"]
            }
        ],
        "assignments": [
            {
                "name": "NPV Calculation Problem Set",
                "description": "Calculate net present value for a series of sample investment projects"
            },
            {
                "name": "Portfolio Risk Analysis",
                "description": "Analyze risk and return tradeoffs across a sample investment portfolio"
            }
        ]
    }
}

def get_course_context(course_id: str):
    try: 
        return COURSE_DATA.get(course_id, {})
    except Exception as e:
        return f"Error retrieving course context for {course_id}: {e}"
    
# Verification Test
if __name__ == "__main__":
    print(get_course_context("CS3354"))
    print(get_course_context("FAKE101"))

