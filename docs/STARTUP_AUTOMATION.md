# Dev Stack Startup

Starts **DB init**, **FastAPI**, **SQS worker**, and **Next.js** from one script.

## Run

From repo root (ensure Postgres and Redis are already running, e.g. via Docker):

```bash
./start-dev.sh
```

- **FastAPI**: http://localhost:8000  
- **Next.js**: http://localhost:3000  
- Logs: `logs/fastapi.log`, `logs/sqs_worker.log`, `logs/nextjs.log`

## Stop

```bash
./stop-dev.sh
```

This kills the FastAPI, SQS worker, and Next.js processes started by `start-dev.sh`.
