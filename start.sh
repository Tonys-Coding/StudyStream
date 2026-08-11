#!/bin/bash
#
# Starts everything: the four backend services and the frontend dev server.
#
#   ./start.sh
#
# Backend only:  ./orchestrator-work/start.sh
# Frontend only: cd classroom-assistant-ui && npm run dev

cd "$(dirname "$0")" || exit 1

echo "Starting AI Classroom Assistant..."
echo ""


if [ ! -d "classroom-assistant-ui/node_modules" ]; then
    echo "ERROR: frontend dependencies are not installed."
    echo "Run: cd classroom-assistant-ui && npm install"
    exit 1
fi


PIDS=()

cleanup() {
    echo ""
    echo "Shutting down..."
    kill "${PIDS[@]}" 2>/dev/null
    wait 2>/dev/null
}

trap cleanup EXIT INT TERM


# Backend. Its own trap stops the four services when this one exits.
./orchestrator-work/start.sh &
PIDS+=($!)


# Frontend
(
    cd classroom-assistant-ui || exit 1
    exec npm run dev
) &
PIDS+=($!)


echo ""
echo "  Frontend  http://localhost:5173"
echo "  API docs  http://127.0.0.1:8001/docs"
echo ""
echo "Press CTRL+C to stop everything."

wait
