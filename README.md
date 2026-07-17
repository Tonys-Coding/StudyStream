# AI Classroom Assistant - Prototype v1

## Overview

This branch (`prototype-v1`) contains the first integrated version of the AI Classroom Assistant project.

The goal of this prototype is to test the communication between different agents using an orchestrator-based architecture.

At this point, we have implemented:

* Orchestrator Agent
* Study Agent communication

The FAQ Agent and Assessment Agent folders are included, but their integration with the Orchestrator will be added in future updates.

---

## Current Workflow

The current workflow is:

```
User Request
      |
      v
Orchestrator Agent (Port 8001)
      |
      v
Study Agent (Port 8003)
      |
      v
Response returned to Orchestrator
      |
      v
User receives response
```

The Orchestrator is responsible for receiving the user's request and deciding which agent should handle it.

Currently, study-related requests are routed to the Study Agent.

---

## Example Request

The user sends the request to the Orchestrator:

Endpoint:

```
POST http://localhost:8001/chat
```

Example JSON:

```json
{
  "message": "Prepare for my CS3354 midterm",
  "user_id": "123",
  "course_id": "CS3354"
}
```

The Orchestrator receives this request, identifies that it is a study request, sends it to the Study Agent, and returns the Study Agent response back to the user.

---

# Project Structure

```
AI-Classroom-Assistant/

├── orchestrator/
│   ├── main.py
│   ├── router.py
│   └── agents.py
│
├── study-agent/
│   ├── main.py
│   ├── agent.py
│   ├── models.py
│   ├── prompts.py
│   └── data.py
│
├── faq-agent/
│   └── main.py
│
├── assessment-agent/
│   └── main.py
│
├── shared/
│   └── requirements.txt
│
├── .env
├── start.sh
└── test_connection.py
```

---

# File Description

## orchestrator/

The Orchestrator is the main entry point for user requests.

### main.py

* Creates the FastAPI application
* Provides the `/chat` endpoint
* Receives user requests
* Sends requests to the correct agent

### router.py

Contains the routing logic.

For now:

* Study request → Study Agent

Future:

* Quiz request → Assessment Agent
* General questions → FAQ Agent

### agents.py

Contains functions used by the Orchestrator to communicate with other agents.

---

## study-agent/

The Study Agent generates study plans based on the user's goal and course information.

### main.py

Runs the Study Agent API.

It receives requests from the Orchestrator and returns the generated study plan.

### agent.py

Contains the main AI logic:

* Loads environment variables
* Creates Azure OpenAI client
* Builds prompts
* Calls the LLM
* Processes the response

### prompts.py

Contains the system prompt and user prompt templates used by the AI model.

### data.py

Currently provides course information for testing.

The data is hard-coded at this stage. Later it can be connected to a database or RAG service.

### models.py

Contains request and response data models using Pydantic.

---

# Shared Folder

## shared/requirements.txt

Contains common Python packages needed by the agents.

Current dependencies:

```
fastapi
uvicorn
openai
python-dotenv
pydantic
requests
```

If an agent needs a package that is specific only to that agent, it can have its own requirements file later.

---

# Environment File

## .env

Stores configuration values such as Azure OpenAI credentials.

Example:

```
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_DEPLOYMENT_NAME=
```

The `.env` file should stay local and should not be pushed to GitHub.

---

# Running the Project

The `start.sh` file starts all agents together.

Current ports:

| Service          | Port |
| ---------------- | ---- |
| FAQ Agent        | 8000 |
| Orchestrator     | 8001 |
| Assessment Agent | 8002 |
| Study Agent      | 8003 |

Run:

```
./start.sh
```

---

# Testing

`test_connection.py` can be used to test communication between services and verify that the APIs are running correctly.

---

# Current Status

Implemented:

✅ Orchestrator service
✅ Study Agent service
✅ Communication between Orchestrator and Study Agent
✅ Basic routing logic

Not implemented yet:

⬜ FAQ Agent integration
⬜ Assessment Agent integration
⬜ Database integration
⬜ RAG service integration
⬜ Frontend interface

This branch represents the first working prototype of the multi-agent architecture.

