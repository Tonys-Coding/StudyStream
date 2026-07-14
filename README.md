# Study Planning & Feedback Agent

This agent generates personalized study plans for students based on their stated goal and course context using Azure OpenAI (GPT-4.1.-mini)

## Status (7/3)

Working MVP
`study/plan` endpoint tested and returning proper, valid structured responses

## Setup

```bash
#Clone the repo
cd Study-Feedback-Agent

#Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # -> For Mac/Linux
.venv\Scripts\activate      # -> For Windows

# Install Dependencies
pip install -r requirements.txt
```

Create a `.env` file in this directory with:

```bash
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_API_KEY=your_key_here
AZURE_DEPLOYMENT_NAME=gpt-4.1-mini
```

## Running

```bash
uvicorn main:app --reload
```

(API docs available at `http://127.0.0.1:8000/docs`)

## Endpoints

| Method | Path          | Description                           |
| ------ | ------------- | ------------------------------------- |
| GET    | `/health`     | Health check                          |
| POST   | `/study/plan` | Generates the personalized study plan |

## Example Request

```json
{
  "user_id": "123",
  "course_id": "CS3354",
  "goal": "Prepare for midterm"
}
```

## Example Response

```json
{
  "success": true,
  "study_plan": ["Review Requirements Engineering fundamentals", "..."],
  "focus_topics": ["Requirements Engineering", "System Architecture"],
  "estimated_hours": 8
}
```

## Architecture

Request -> FastAPI (main.py)

1. Course Lookup (data.py)
2. Prompt assembly (prompts.py)
3. Azure OpenAI Chat Completions (agent.py)
4. Structured JSON response
