#!/bin/bash
#
# Starts the four backend services.
# To start the frontend as well, use ../start.sh instead.

echo "Starting AI Classroom Assistant backend..."

# Run from the folder this script lives in, so the relative paths below
# work no matter where you invoke it from.
cd "$(dirname "$0")" || exit 1


# Activate virtual environment
# Override with: VENV=../some-other-venv ./start.sh
VENV="${VENV:-../.venv-1}"

if [ ! -f "$VENV/bin/activate" ]; then
    echo "ERROR: no virtual environment at $VENV"
    echo "Create one, or point at an existing one with: VENV=path ./start.sh"
    exit 1
fi

# Absolute, because the services below cd into their own folders.
VENV="$(cd "$VENV" && pwd)"

source "$VENV/bin/activate"


# The agents read Azure and Supabase credentials from this file.
if [ ! -f ".env" ]; then
    echo "ERROR: .env not found in $(pwd)"
    echo "Copy it from the project root: cp ../.env .env"
    exit 1
fi


PIDS=()

start_service() {
    local name="$1"
    local dir="$2"
    local port="$3"

    echo "Starting $name on port $port..."

    (
        cd "$dir" || exit 1
        # --reload-dir ../shared: the services import ../shared/common.py, and
        # by default only the service's own folder is watched, so an edit there
        # would be ignored until a manual restart.
        #
        # Run uvicorn through the venv's python rather than its launcher
        # script. The launcher hardcodes the folder the venv was created in,
        # so it breaks the moment the project folder is moved or renamed.
        exec "$VENV/bin/python" -m uvicorn main:app --reload --reload-dir . --reload-dir ../shared --host 127.0.0.1 --port "$port"
    ) &

    PIDS+=($!)
}


# Stop only the services this script started - not the parent shell.
cleanup() {
    echo ""
    echo "Stopping services..."
    kill "${PIDS[@]}" 2>/dev/null
    wait 2>/dev/null
}

trap cleanup EXIT INT TERM


start_service "FAQ Agent"        faq-agent        8000
start_service "Assessment Agent" assessment-agent 8002
start_service "Study Agent"      study-agent      8003
start_service "Orchestrator"     orchestrator     8001


echo ""
echo "Backend running. API docs at http://127.0.0.1:8001/docs"
echo "Press CTRL+C to stop."

wait
