# AVAE Phase 1–5: Complete Flow Testing Guide

End-to-end testing for Phases 1 (Foundation) through 5 (HITL & Checkpoint Resume).

---

## Prerequisites

### 1. Infrastructure Running

```bash
cd document-processor

# Start PostgreSQL + Redis
docker-compose up -d postgres redis

# Wait ~5 seconds, then init DB
python3 -c "from app.database import init_db; init_db()"
```

### 2. Environment (.env)

Required:
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- `S3_BUCKET_NAME`, `SQS_QUEUE_URL`
- `LLAMA_CLOUD_API_KEY` (or extraction may fall back to legacy)
- `OPENAI_API_KEY` (for structured extraction)

Optional (for real API verification):
- `COMPANIES_HOUSE_API_KEY` — Companies House
- `EPC_API_EMAIL`, `EPC_API_KEY` — EPC Open Data
- `LAND_REGISTRY_USERNAME`, `LAND_REGISTRY_PASSWORD` — HM Land Registry

**Note:** Without external API keys, `fetch_api` returns `None` → verification returns `DISCREPANCY_FLAG` → document goes to `PENDING_HUMAN_REVIEW`. This is ideal for testing HITL without real APIs.

---

## Services to Run (3 terminals)

### Terminal 1: FastAPI Backend

```bash
cd document-processor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: SQS Worker

```bash
cd document-processor
python3 -m app.sqs_worker
```

### Terminal 3: For curl/API tests (or use Streamlit)

Keep this for running test commands.

---

## Test Flow Overview

| Phase | What to Test | How |
|-------|--------------|-----|
| 1 | Upload with audit_target, audit_logs | Upload API + DB check |
| 2 | API fetch, verification | Worker logs; audit_logs table |
| 3 | LangGraph pipeline | Worker processes task; status flow |
| 4 | Bursting, extraction | Worker logs; extracted_json in audit_logs |
| 5 | HITL: Override, Manual Correction, Request Client Remediation, listing, TTL, remediation upload | HITL API endpoints |

---

## Phase 1: Foundation

### 1.1 Health Check

```bash
curl -s http://localhost:8000/health | jq
```

Expected: `"status": "healthy"`, `redis_connected: true`

### 1.2 Upload with audit_target

```bash
# Upload a PDF with audit_target=epc (default)
curl -X POST "http://localhost:8000/upload?user_id=1&audit_target=epc" \
  -F "files=@/path/to/your/test.pdf"
```

Expected response:
```json
{
  "task_ids": ["1"],
  "total_files": 1,
  "message": "Successfully queued 1 file(s) for processing"
}
```

Save `task_id` (e.g. `1`) for later steps.

### 1.3 Check Document in DB

```bash
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT id, filename, status, audit_target, created_at 
  FROM documents 
  ORDER BY id DESC LIMIT 3;
"
```

Expected: `audit_target = epc`, `status` progresses: PENDING → PROCESSING → COMPLETED or PENDING_HUMAN_REVIEW

---

## Phase 2 & 3 & 4: Pipeline (Worker)

The SQS worker runs the LangGraph pipeline. Watch Terminal 2 for logs.

### Expected Worker Flow

```
📨 Received message for task: 1 (audit_target=epc)
📥 Downloading from S3: uploads/...
📄 Burst into N page(s)           ← Phase 4: PyMuPDF burst
📊 Task 1: 40% complete           ← Phase 4: extract_parallel, merge, normalize
📊 Task 1: 70% complete           ← Phase 2: fetch_api, verify
📋 Human review required...       ← Phase 3: DISCREPANCY_FLAG → human_review
💾 Saved result to PostgreSQL     ← persist
```

### 2.1 Check audit_logs (Phase 2)

```bash
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT id, document_id, audit_target, verification_status, 
         jsonb_pretty(extracted_json) as extracted,
         discrepancy_flags
  FROM audit_logs 
  ORDER BY id DESC LIMIT 1;
"
```

Expected: `verification_status` = `DISCREPANCY_FLAG` (if no API keys) or `VERIFIED` (if APIs return matching data). `extracted_json` has structured fields (Phase 1.4).

### 2.2 Check Task Status

```bash
TASK_ID=1  # use your task_id
curl -s "http://localhost:8000/status/$TASK_ID" | jq
```

Expected: `status` = `PENDING_HUMAN_REVIEW` (when DISCREPANCY_FLAG) or `COMPLETED` (when VERIFIED).

---

## Phase 5: HITL Flow

### 5.1 List Checkpoints

```bash
curl -s "http://localhost:8000/hitl/checkpoints?page=1&page_size=10" | jq
```

Expected: List of documents with `status` = `PENDING_HUMAN_REVIEW` or `AWAITING_CLIENT_REMEDIATION`.

### 5.2 Preview Remediation Email

```bash
CHECKPOINT_ID=1  # use a PENDING_HUMAN_REVIEW checkpoint
curl -s "http://localhost:8000/hitl/remediation-email/$CHECKPOINT_ID?message=Please%20provide%20updated%20document" | jq
```

Expected: `{ "subject": "...", "body": "..." }`

### 5.3 Request Client Remediation

```bash
curl -X POST "http://localhost:8000/hitl/request-client-remediation" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_id": "1", "message": "Please upload corrected EPC certificate"}'
```

Expected: `status: AWAITING_CLIENT_REMEDIATION`, `email_draft: { subject, body }`

### 5.4 Override (use a different PENDING_HUMAN_REVIEW checkpoint)

```bash
# First ensure you have a PENDING_HUMAN_REVIEW doc (not AWAITING_CLIENT_REMEDIATION)
curl -X POST "http://localhost:8000/hitl/override" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_id": "2"}'
```

Expected: `success: true`, `status: VERIFIED`

### 5.5 Manual Correction

```bash
curl -X POST "http://localhost:8000/hitl/manual-correction" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_id": "3", "corrections": {"company_number": "12345678"}}'
```

Expected: `success: true`, `status: VERIFIED`

### 5.6 Remediation Upload (attach new file to AWAITING_CLIENT_REMEDIATION)

After step 5.3, document 1 is `AWAITING_CLIENT_REMEDIATION`. Upload a replacement:

```bash
curl -X POST "http://localhost:8000/upload?user_id=1&remediation_for_checkpoint_id=1" \
  -F "files=@/path/to/corrected.pdf"
```

Expected: `task_ids: ["1"]`, `message: "Remediation file queued for processing"`. Worker will re-process the same document with the new file.

### 5.7 Checkpoint TTL (expire old PENDING_HUMAN_REVIEW)

```bash
# Manual trigger
curl -X POST "http://localhost:8000/hitl/expire-checkpoints"
```

Expected: `{ "expired_count": N, "message": "..." }`

Or run the cron script:
```bash
python3 scripts/expire_hitl_checkpoints.py
```

---

## Quick End-to-End Script

Save as `test_avae_flow.sh`:

```bash
#!/bin/bash
set -e
API="http://localhost:8000"
PDF="${1:-./test.pdf}"

echo "1. Health check"
curl -s "$API/health" | jq .status

echo "2. Upload with audit_target=epc"
RESP=$(curl -s -X POST "$API/upload?user_id=1&audit_target=epc" -F "files=@$PDF")
TASK_ID=$(echo "$RESP" | jq -r '.task_ids[0]')
echo "   task_id=$TASK_ID"

echo "3. Wait for processing (poll status every 5s)..."
for i in {1..24}; do
  STATUS=$(curl -s "$API/status/$TASK_ID" | jq -r '.status')
  echo "   [$i] status=$STATUS"
  [[ "$STATUS" == "COMPLETED" ]] || [[ "$STATUS" == "PENDING_HUMAN_REVIEW" ]] && break
  sleep 5
done

echo "4. List checkpoints"
curl -s "$API/hitl/checkpoints?page=1&page_size=5" | jq '.checkpoints | length'

echo "5. If PENDING_HUMAN_REVIEW: preview remediation email"
curl -s "$API/hitl/remediation-email/$TASK_ID" | jq .subject

echo "Done. task_id=$TASK_ID"
```

Usage: `chmod +x test_avae_flow.sh && ./test_avae_flow.sh /path/to/test.pdf`

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Upload fails 400 | Ensure PDF file exists, `audit_target` is epc/companies_house/hm_land_registry |
| Status stuck PENDING | SQS worker not running; check SQS queue URL and AWS credentials |
| No audit_logs row | Worker may have failed; check worker logs for extraction/API errors |
| Override/Manual Correction fails | Document must be `PENDING_HUMAN_REVIEW` |
| Remediation upload fails | Document must be `AWAITING_CLIENT_REMEDIATION`; same user_id |
| Expire returns 0 | No documents in PENDING_HUMAN_REVIEW older than 7 days |

---

## Summary: What Each Phase Validates

| Phase | Validated By |
|-------|--------------|
| 1 | Upload with audit_target; documents + audit_logs in DB |
| 2 | audit_logs has verification_status, discrepancy_flags; API clients called (if keys set) |
| 3 | Worker invokes LangGraph; VERIFIED → persist, DISCREPANCY_FLAG → human_review |
| 4 | Worker logs show burst, classify, extract; extracted_json in audit_logs |
| 5 | HITL endpoints work; checkpoint listing; remediation upload; TTL script |
