# Assessment Agent

## Overview

This branch contains the development of the **Assessment Agent** for the AI Classroom Assistant project.

The goal of this agent is to receive a request from a user, use the provided course information, communicate with Azure OpenAI, and generate assessment questions.

For this first prototype, the agent uses a simple hard-coded course context. The purpose is to make sure the basic workflow is working correctly before adding more advanced features.

---

## Current Status

The Assessment Agent is currently able to:

* Receive a quiz generation request through a FastAPI API
* Read basic course information from `data.py`
* Create a prompt using the course information and user request
* Communicate with Azure OpenAI
* Generate multiple-choice questions
* Return the generated questions in a structured format

At this stage, the agent does **not** use RAG yet. The connection with the RAG system will be added in a future version so the agent can use actual course materials, such as lecture notes, slides, and other class documents, when creating assessments.

---

## How It Works

The current workflow is:

```text
User Request
      |
      v
Assessment Agent API
      |
      v
Course Information (data.py)
      |
      v
Prompt Creation (prompts.py)
      |
      v
Azure OpenAI
      |
      v
Generated Quiz Response
```

Currently, `data.py` contains simple course information used for testing. The Assessment Agent uses this information to create a prompt and sends it to Azure OpenAI. The response from Azure OpenAI is then processed and returned to the user.

Later, `data.py` will be replaced or extended with a connection to the RAG system so the agent can generate questions based on real course content.

---

## API

The Assessment Agent runs on port **8002**.

### Generate Quiz

Endpoint:

```
POST /generate_quiz
```

Example request:

```json
{
  "user_id": "123",
  "course_id": "CS3354",
  "topic": "Requirements Engineering",
  "num_questions": 3
}
```

Example response:

```json
{
  "success": true,
  "questions": [
    {
      "question": "What is the primary goal of requirements engineering?",
      "choices": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "answer": "Option B"
    }
  ]
}
```

---

## Project Structure

```
assessment-agent/

├── main.py
│   FastAPI application.
│   Defines the API endpoints and handles requests.

├── agent.py
│   Main logic for the Assessment Agent.
│   Handles the course context, creates prompts,
│   calls Azure OpenAI, and processes the response.

├── models.py
│   Defines the request and response formats.

├── prompts.py
│   Contains the prompts used when communicating
│   with Azure OpenAI.

└── data.py
    Contains temporary hard-coded course information
    used for testing.
```

---

## Running the Agent

From the `assessment-agent` folder:

```bash
uvicorn main:app --reload --port 8002
```

The agent will run at:

```
http://localhost:8002
```

Health check:

```
GET /health
```

Generate quiz:

```
POST /generate_quiz
```

---

## Notes

This is the first prototype version of the Assessment Agent.

The main focus of this branch is to build and test the Assessment Agent independently:

* Receive requests
* Communicate with Azure OpenAI
* Generate assessment questions
* Return responses correctly

The next steps will be improving the agent by connecting it with the RAG system and using real course materials instead of hard-coded information.

The integration between the Assessment Agent and the Orchestrator will be handled separately.

```
```
