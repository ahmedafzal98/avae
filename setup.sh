#!/usr/bin/env bash
# AVAE — One-command setup for local development (Mac)
# Usage: ./setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOC_PROC="$SCRIPT_DIR/document-processor"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "[$(date '+%H:%M:%S')] $*"; }
ok()  { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err() { echo -e "${RED}✗${NC} $*" >&2; }

# --- Prerequisites ---
log "Checking prerequisites..."

check_cmd() {
  if command -v "$1" &>/dev/null; then
    ok "$1: $(command -v "$1")"
    return 0
  else
    err "$1 not found. Install it and try again."
    return 1
  fi
}

MISSING=0
check_cmd docker || MISSING=1
check_cmd python3 || MISSING=1
check_cmd node || MISSING=1
check_cmd npm || MISSING=1

if [[ $MISSING -eq 1 ]]; then
  err "Prerequisites missing. See SETUP.md for install instructions."
  exit 1
fi

# Version checks (soft)
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "?")
NODE_VER=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1 || echo "?")
[[ "$PY_VER" < "3.11" ]] && warn "Python 3.11+ recommended (you have $PY_VER)"
[[ "$NODE_VER" < "18" ]] && warn "Node 18+ recommended (you have $NODE_VER)"

# --- Env files ---
log "Setting up environment files..."

if [[ ! -f "$DOC_PROC/.env" ]]; then
  if [[ -f "$DOC_PROC/env.example" ]]; then
    cp "$DOC_PROC/env.example" "$DOC_PROC/.env"
    ok "Created document-processor/.env (from env.example)"
    warn "Edit document-processor/.env and add your API keys (AWS, OpenAI, LlamaCloud, Companies House)"
  else
    err "document-processor/env.example not found"
    exit 1
  fi
else
  ok "document-processor/.env exists"
fi

if [[ ! -f "$FRONTEND_DIR/.env.local" ]]; then
  if [[ -f "$FRONTEND_DIR/.env.example" ]]; then
    cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env.local"
    ok "Created frontend/.env.local (from .env.example)"
    warn "Edit frontend/.env.local and add Clerk keys"
  else
    err "frontend/.env.example not found"
    exit 1
  fi
else
  ok "frontend/.env.local exists"
fi

# --- Docker Compose (V1 or V2) ---
if docker compose version &>/dev/null; then
  COMPOSE_CMD="docker compose"
else
  COMPOSE_CMD="docker-compose"
fi

# --- Docker ---
log "Starting PostgreSQL and Redis..."

cd "$DOC_PROC"
if ! $COMPOSE_CMD ps postgres 2>/dev/null | grep -q "Up"; then
  $COMPOSE_CMD up -d postgres redis
  ok "Started postgres and redis"
  log "Waiting for PostgreSQL (15s)..."
  sleep 15
else
  ok "PostgreSQL and Redis already running"
fi

# --- pgvector ---
log "Ensuring pgvector extension..."
for i in 1 2 3 4 5; do
  if $COMPOSE_CMD exec -T postgres psql -U docuser -d document_processor -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
    ok "pgvector ready"
    break
  fi
  [[ $i -eq 5 ]] && warn "pgvector init skipped (postgres may still be starting)"
  sleep 2
done

# --- Python deps ---
log "Installing Python dependencies..."
cd "$DOC_PROC"
pip install -q -r requirements.txt
ok "Python dependencies installed"

# --- DB init ---
log "Initializing database..."
python3 -c "
from app.database import init_db
init_db()
print('OK')
" || { err "DB init failed"; exit 1; }
ok "Database initialized"

# --- Node deps ---
log "Installing Node dependencies..."
cd "$FRONTEND_DIR"
npm install --silent
ok "Node dependencies installed"

# --- Done ---
echo ""
echo -e "${GREEN}Setup complete.${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit document-processor/.env — add AWS, OpenAI, LlamaCloud, Companies House keys"
echo "  2. Edit frontend/.env.local — add Clerk keys (NEXT_PUBLIC_CLERK_*, CLERK_SECRET_KEY)"
echo "  3. Run: ./start-dev.sh"
echo ""
echo "URLs:"
echo "  Next.js:  http://localhost:3000"
echo "  FastAPI:  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo ""
