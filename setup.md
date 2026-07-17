# AI Classroom Assistant

## Development Environment Setup

### Prerequisites

Install the following software:

* Python 3.10+

---

# Create Virtual Environment

```bash
python3 -m venv venv
```

Activate the virtual environment:

Mac/Linux:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

---

# Install Dependencies

```bash
pip install fastapi uvicorn requests
```

Verify installation:

```bash
pip list
```

You should see:

* fastapi
* uvicorn
* requests

---

# Project Structure

```text
AI-Classroom-Assistant/
│
├── orchestrator/
│   └── main.py
│
├── faq-agent/
│   └── main.py
│
├── assessment-agent/
│   └── main.py
│
├── study-agent/
│   └── main.py
│
├── docs/
│
├── tests/
│   └── test_orchestrator.py
│
├── start.sh
│
└── venv/
```

---
# Running Services

## 1- Running Individual Services

Open a separate terminal for each service.

### FAQ Agent

```bash
cd faq-agent
source ../venv/bin/activate
uvicorn main:app --reload --port 8000
```

---

### Assessment Agent

```bash
cd assessment-agent
source ../venv/bin/activate
uvicorn main:app --reload --port 8002
```

---

### Study Agent

```bash
cd study-agent
source ../venv/bin/activate
uvicorn main:app --reload --port 8003
```

---

### Orchestrator

```bash
cd orchestrator
source ../venv/bin/activate
uvicorn main:app --reload --port 8001
```

---

# 2- Running All Services

If `start.sh` is configured:

```bash
chmod +x start.sh
./start.sh
```

---

# API Documentation

FastAPI automatically generates interactive API documentation.

Open:

FAQ Agent

```text
http://127.0.0.1:8000/docs
```

Assessment Agent

```text
http://127.0.0.1:8002/docs
```

Study Agent

```text
http://127.0.0.1:8003/docs
```

Orchestrator

```text
http://127.0.0.1:8001/docs
```

---

# Running Tests

Open a new terminal.

Activate the virtual environment:

```bash
source venv/bin/activate
```

Run:

```bash
python tests/test_orchestrator.py
```

---

# Current MVP Scope

Current prototype includes:

* Orchestrator Agent
* FAQ Agent
* Assessment Agent
* Study Planning Agent
* Agent-to-agent communication
* Local API integration
* Automated test script

Future phases include:

* RAG integration
* PostgreSQL/Supabase integration
* Student history
* Progress tracking
* Analytics
* Frontend integration
* LangGraph workflows

---

# Expected System Flow

```text
User
 ↓
Orchestrator
 ↓
FAQ Agent / Assessment Agent / Study Agent
 ↓
Response Returned
```

The goal of this setup is to ensure all team members can run the system locally and understand how the agents communicate before adding RAG, databases, or frontend components.
