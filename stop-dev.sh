#!/usr/bin/env bash
# Stop FastAPI, SQS worker, and Next.js started by start-dev.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.dev-stack.pids"

echo "Stopping dev processes..."
if [ -f "$PID_FILE" ]; then
  while read -r pid; do
    [ -z "$pid" ] && continue
    kill "$pid" 2>/dev/null && echo "Stopped PID $pid"
  done <"$PID_FILE"
  rm -f "$PID_FILE"
else
  echo "No .dev-stack.pids found."
fi
echo "Done."
