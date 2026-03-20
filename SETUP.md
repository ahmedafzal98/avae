# AVAE — Local Setup Guide (Mac)

This guide ensures the AVAE project runs seamlessly on any Mac. Follow these steps for a fresh machine.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| **Docker Desktop** | Latest | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) |
| **Python** | 3.11+ | `brew install python@3.11` or [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ (20 recommended) | `brew install node@20` or [nodejs.org](https://nodejs.org/) |
| **npm** | 9+ | Bundled with Node.js |

### Quick version check

```bash
docker --version    # Docker version 24+
python3 --version   # Python 3.11+
node --version      # v18+ or v20+
npm --version       # 9+
```

---

## One-Command Setup (Recommended)

```bash
./setup.sh
```

This script will:

1. Check prerequisites (Docker, Python, Node)
2. Copy `.env.example` → `.env` in both backend and frontend (if missing)
3. Start PostgreSQL and Redis via Docker
4. Initialize the database
5. Install Python and Node dependencies
6. Prompt you to fill in API keys in `.env` files

Then start the app:

```bash
./start-dev.sh
```

---

## Manual Setup

### Step 1: Clone and enter project

```bash
cd /path/to/redis   # or your project directory
```

### Step 2: Start infrastructure (PostgreSQL, Redis)

```bash
cd document-processor
cp env.example .env
# Edit .env: set POSTGRES_PASSWORD and PGADMIN_DEFAULT_PASSWORD (required by docker-compose)

docker-compose up -d postgres redis
```

Wait ~10 seconds for PostgreSQL to be ready.

### Step 3: Initialize database

```bash
cd document-processor
pip install -r requirements.txt
python3 -c "from app.database import init_db; init_db(); print('OK')"
```

### Step 4: Enable pgvector (if not already)

```bash
docker-compose exec postgres psql -U docuser -d document_processor \
  -f /docker-entrypoint-initdb.d/init.sql
```

### Step 5: Configure backend environment

Edit `document-processor/.env` and set:

| Variable | Required | Notes |
|----------|----------|-------|
| `AWS_ACCESS_KEY_ID` | Yes | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS credentials |
| `AWS_REGION` | Yes | e.g. `us-east-1` |
| `S3_BUCKET_NAME` | Yes | S3 bucket for uploads |
| `SQS_QUEUE_URL` | Yes | SQS queue URL |
| `LLAMA_CLOUD_API_KEY` | Yes | [LlamaCloud](https://cloud.llamaindex.ai/api-key) |
| `OPENAI_API_KEY` | Yes | [OpenAI](https://platform.openai.com/api-keys) |
| `POSTGRES_PASSWORD` | Yes | Must match docker-compose |
| `COMPANIES_HOUSE_API_KEY` | For demo | [Companies House](https://developer.company-information.service.gov.uk/) |

### Step 6: Configure frontend environment

```bash
cd frontend
cp .env.example .env.local
```

Edit `frontend/.env.local`:

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` for local |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | [Clerk](https://dashboard.clerk.com) |
| `CLERK_SECRET_KEY` | Yes | Clerk dashboard |

### Step 7: Install frontend dependencies

```bash
cd frontend
npm install
```

### Step 8: Start the application

From the project root:

```bash
./start-dev.sh
```

Or manually in separate terminals:

```bash
# Terminal 1 — FastAPI
cd document-processor && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — SQS Worker
cd document-processor && python3 -m app.sqs_worker

# Terminal 3 — Next.js
cd frontend && npm run dev
```

---

## URLs

| Service | URL |
|---------|-----|
| Next.js (AVAE UI) | http://localhost:3000 |
| FastAPI (backend) | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |

---

## Stopping

```bash
# Stop app processes
kill $(cat .dev-stack.pids)

# Stop Docker (optional)
cd document-processor && docker-compose down
```

---

## Troubleshooting

### "Connection refused" on port 5433

PostgreSQL not running. Start it:

```bash
cd document-processor && docker-compose up -d postgres
```

### "Connection refused" on port 6379

Redis not running:

```bash
cd document-processor && docker-compose up -d redis
```

### "Extension vector does not exist"

Run the init script:

```bash
docker-compose exec postgres psql -U docuser -d document_processor \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Python module not found

Ensure you're in the correct directory and have installed deps:

```bash
cd document-processor
pip install -r requirements.txt
```

### Node / npm issues

Use the recommended Node version:

```bash
nvm use    # if using nvm and .nvmrc exists
# or
brew install node@20
```

### SQS / S3 errors

Verify AWS credentials and that the S3 bucket and SQS queue exist. The queue must be in the same region as `AWS_REGION`.

---

## File Structure (Portability)

```
redis/
├── SETUP.md              # This file
├── setup.sh              # One-command setup
├── start-dev.sh          # Start app (assumes infra is running)
├── env.example           # Root env template (reference)
├── document-processor/
│   ├── .env              # Backend config (create from env.example)
│   ├── env.example       # Backend template
│   ├── docker-compose.yml
│   └── ...
└── frontend/
    ├── .env.local        # Frontend config (create from .env.example)
    ├── .env.example      # Frontend template
    └── ...
```

**Never commit** `.env` or `.env.local` — they contain secrets. Both are in `.gitignore`.
