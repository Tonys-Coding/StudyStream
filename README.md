# Assessment Agent - Development Branch

## Overview

This branch is dedicated to the development of the **Assessment Agent** for the AI Classroom Assistant project.

The purpose of this branch is to build and test the Assessment Agent independently before integrating it into the shared project.

This branch was originally created from the `main` branch and will later be updated with changes from the `prototype-v1` branch. This mirrors the workflow that each team member will follow as the project evolves.

---

## Goal

The Assessment Agent is responsible for generating quizzes and assessments based on a student's course and learning goals.

For the first prototype, the implementation will be intentionally simple and use hard-coded data where appropriate. The focus is on building the agent architecture and integrating it with the Orchestrator, rather than creating a complete assessment system.

---

## Planned Features

The first version of the Assessment Agent will:

* Accept requests from the Orchestrator
* Generate multiple-choice quiz questions using Azure OpenAI
* Return quiz questions in a structured JSON format
* Handle basic error checking and API responses

---

## Planned API

Example request:

```json
{
  "user_id": "123",
  "course_id": "CS3354",
  "topic": "Requirements Engineering",
  "num_questions": 5
}
```

Example response:

```json
{
  "success": true,
  "questions": [
    {
      "question": "What is a functional requirement?",
      "choices": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "answer": "Option A"
    }
  ]
}
```

---

## Expected Project Structure

```text
assessment-agent/

├── main.py          # FastAPI application and API endpoints
├── agent.py         # Main Assessment Agent logic
├── models.py        # Request and response models
├── prompts.py       # Prompt templates
└── data.py          # Temporary hard-coded course data
```

---

## Development Notes

This branch is intended for Assessment Agent development only.

As the project progresses, this branch will be updated with changes from the `prototype-v1` integration branch so that it stays compatible with the latest project architecture.

After the Assessment Agent is complete and tested, it can be merged back into the integration branch and eventually into `main`.

---

## Current Status

* ✅ Branch created
* ⏳ Assessment Agent implementation in progress
* ⏳ Integration with Orchestrator planned
* ⏳ Testing and documentation to be added
