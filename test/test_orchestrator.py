import requests

ORCHESTRATOR_URL = "http://127.0.0.1:8001/chat"


tests = [
    {
        "name": "FAQ Test",
        "message": "What is Newton's Second Law?"
    },
    {
        "name": "Quiz Test",
        "message": "Generate a quiz on Newton's Second Law"
    },
    {
        "name": "Study Plan Test",
        "message": "Make a study plan for Physics exam"
    }
]


for test in tests:
    print("\n==============================")
    print("Running:", test["name"])

    response = requests.post(
        ORCHESTRATOR_URL,
        json={"message": test["message"]}
    )

    print("Status Code:", response.status_code)
    print("Response:")
    print(response.json())
