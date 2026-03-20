#!/bin/bash
set -e

echo "Starting SQS worker in background..."
python -m app.sqs_worker &
WORKER_PID=$!
echo "SQS worker started (PID: $WORKER_PID)"

echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
SERVER_PID=$!
echo "FastAPI server started (PID: $SERVER_PID)"

# If either process exits, kill the other and exit
wait -n
EXIT_CODE=$?
echo "A process exited with code $EXIT_CODE, shutting down..."
kill $WORKER_PID $SERVER_PID 2>/dev/null
exit $EXIT_CODE
