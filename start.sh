#!/bin/bash
 
echo "Starting AI Classroom Assistant..."
 
# Activate virtual environment
source venv/bin/activate
 
# Install/update dependencies
echo "Checking and installing dependencies..."
pip install -r shared/requirements.txt
 
# Start FAQ Agent
echo "Starting FAQ Agent on port 8000..."
(
    cd faq-agent
    uvicorn main:app --reload --port 8000
) &
 
 
# Start Assessment Agent
echo "Starting Assessment Agent on port 8002..."
(
    cd assessment-agent
    uvicorn main:app --reload --port 8002
) &
 
 
# Start Study Agent
echo "Starting Study Agent on port 8003..."
(
    cd study-agent
    uvicorn main:app --reload --port 8003
) &
 
 
# Start Orchestrator
echo "Starting Orchestrator on port 8001..."
(
    cd orchestrator
    uvicorn main:app --reload --port 8001
) &
 
 
echo "All services started!"
echo "Press CTRL+C to stop all services"
 
 
# Keep script running
wait