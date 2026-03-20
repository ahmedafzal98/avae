#!/usr/bin/env bash
# Start: DB init, FastAPI, SQS worker, Next.js.
# Usage: ./start-dev.sh
# Prerequisite: Run ./setup.sh first (starts Postgres + Redis via Docker)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOC_PROC="$SCRIPT_DIR/document-processor"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/.dev-stack.pids"

mkdir -p "$LOG_DIR"
: >"$PID_FILE"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Pre-check: Postgres and Redis must be running
check_port() {
  python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
try:
  s.connect(('127.0.0.1', $1))
  s.close()
  exit(0)
except Exception:
  exit(1)
" 2>/dev/null
}
if ! check_port 5433; then
  echo "Error: PostgreSQL not reachable on port 5433. Run ./setup.sh first." >&2
  exit 1
fi
if ! check_port 6379; then
  echo "Error: Redis not reachable on port 6379. Run ./setup.sh first." >&2
  exit 1
fi

# 1. Connection to DB (init)
log "Initializing database..."
(cd "$DOC_PROC" && python3 -c "
from app.database import init_db
init_db()
print('OK')
" 2>>"$LOG_DIR/init_db.log") || { echo "DB init failed. Check $LOG_DIR/init_db.log" >&2; exit 1; }
log "Database ready."

# 2. FastAPI
log "Starting FastAPI..."
(cd "$DOC_PROC" && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 >>"$LOG_DIR/fastapi.log" 2>&1) &
echo $! >>"$PID_FILE"

# 3. SQS worker
log "Starting SQS worker..."
(cd "$DOC_PROC" && python3 -m app.sqs_worker >>"$LOG_DIR/sqs_worker.log" 2>&1) &
echo $! >>"$PID_FILE"

# 4. Next.js frontend
log "Starting Next.js..."
(cd "$FRONTEND_DIR" && npm run dev >>"$LOG_DIR/nextjs.log" 2>&1) &
echo $! >>"$PID_FILE"

log "Done. FastAPI: http://localhost:8000  Next.js: http://localhost:3000  Logs: $LOG_DIR/"
log "Stop with: kill \$(cat $PID_FILE)"
wait
