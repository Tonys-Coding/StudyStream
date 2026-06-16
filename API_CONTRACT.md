# AI Classroom Assistant API Contract

## Version

1.0

## Purpose

This document defines the communication interfaces between the frontend, orchestrator, and specialized agents within the AI Classroom Assistant system.

The goal is to ensure all team members build services that communicate using consistent request and response formats.

---

# System Architecture

Frontend (React + TypeScript)

↓

Orchestrator Service (FastAPI)

↓

FAQ Agent | Quiz & Assessment Agent | Study Planning & Feedback Agent

↓

Knowledge Sources (Hardcoded Data → Future RAG)

---

# Standard Request Object

All requests sent to the orchestrator must follow the structure below.

```json
{
  "user_id": "123",
  "course_id": "CS3354",
  "query": "What topics are covered on the midterm?"
}
```

### Fields

| Field     | Type   | Description               |
| --------- | ------ | ------------------------- |
| user_id   | string | Unique student identifier |
| course_id | string | Course identifier         |
| query     | string | Student request           |

---

# Standard Response Object

```json
{
  "success": true,
  "agent": "faq",
  "response": {}
}
```

### Fields

| Field    | Type    | Description                |
| -------- | ------- | -------------------------- |
| success  | boolean | Request status             |
| agent    | string  | Agent that handled request |
| response | object  | Agent output               |

---

# Orchestrator API

## POST /orchestrator/query

### Description

Main entry point for all user requests.

The orchestrator determines which agent(s) should process the request.

### Request

```json
{
  "user_id": "123",
  "course_id": "CS3354",
  "query": "Generate a quiz on Chapter 4"
}
```

### Response

```json
{
  "success": true,
  "agent": "quiz",
  "response": {
    "questions": [
      {
        "question": "What is RAG?",
        "answer": "Retrieval-Augmented Generation"
      }
    ]
  }
}
```

---

# FAQ Agent API

## POST /faq/query

### Description

Provides answers to course-related questions.

### Request

```json
{
  "query": "What topics are covered on the midterm?"
}
```

### Response

```json
{
  "answer": "The midterm covers Chapters 1 through 5."
}
```

---

# Quiz & Assessment Agent API

## POST /quiz/generate

### Description

Generates practice quizzes and review questions.

### Request

```json
{
  "topic": "Chapter 4"
}
```

### Response

```json
{
  "questions": [
    {
      "question": "Define Retrieval-Augmented Generation.",
      "answer": "A technique combining retrieval and LLM generation."
    }
  ]
}
```

---

# Study Planning & Feedback Agent API

## POST /study/plan

### Description

Generates personalized study recommendations and plans.

### Request

```json
{
  "goal": "Prepare for midterm"
}
```

### Response

```json
{
  "study_plan": [
    "Review Chapters 1-2",
    "Review Chapters 3-4",
    "Take a practice quiz",
    "Review missed concepts"
  ]
}
```

---

# Error Response Format

All services should return errors in a consistent format.

```json
{
  "success": false,
  "message": "Invalid request."
}
```

---

# Initial Development Notes

For the MVP, agents will use hardcoded course data and predefined responses.

Example:

```json
{
  "midterm_topics": [
    "Chapter 1",
    "Chapter 2",
    "Chapter 3",
    "Chapter 4",
    "Chapter 5"
  ]
}
```

This allows development and integration to proceed before the course database and RAG pipeline are available.

---

# Future Enhancements

Planned additions include:

* Supabase Authentication
* Student Progress Tracking
* RAG Retrieval Pipeline
* pgvector Integration
* Instructor Analytics
* Multi-Course Support

These enhancements should not require changes to the core API structure defined in this document.
