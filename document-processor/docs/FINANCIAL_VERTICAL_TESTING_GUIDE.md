# Financial Vertical — Complete Testing Guide

How to test the full flow of the Financial (SEC / Stock Market) industry vertical in AVAE.

---

## Prerequisites

Before testing, ensure:

- [ ] **Backend running:** FastAPI on port 8000
- [ ] **SQS worker running:** Processing messages from the queue
- [ ] **Frontend running:** Next.js on port 3000 (optional for API-only tests)
- [ ] **PostgreSQL, Redis, S3, SQS** configured and reachable
- [ ] **Environment variables:** `OPENAI_API_KEY`, `LLAMA_CLOUD_API_KEY` (for extraction)

**Start full stack:**
```bash
./start-dev.sh
```

---

## 1. Unit Tests (Verification Logic)

Run the verification module tests to confirm financial comparison logic works.

```bash
cd document-processor
python -c "
from tests.test_verification import test_all
test_all()
"
```

**Add financial tests** (if not yet added) to `tests/test_verification.py`:

```python
def test_financial_verified():
    extracted = {"cik": "320193", "company_name": "Apple Inc.", "revenue": "383285000000", "net_income": "96995000000"}
    api = {"cik": "320193", "company_name": "Apple Inc.", "revenue": 383285000000, "net_income": 96995000000}
    result = verify_extraction("financial", extracted, api)
    assert result.status == "VERIFIED"

def test_financial_discrepancy():
    extracted = {"cik": "320193", "revenue": "400000000000"}
    api = {"cik": "320193", "revenue": 383285000000}
    result = verify_extraction("financial", extracted, api)
    assert result.status == "DISCREPANCY_FLAG"
```

---

## 2. SEC EDGAR Client (Standalone)

Verify the SEC API client works without running the full pipeline.

```bash
cd document-processor
python -c "
from app.clients.sec_edgar import fetch_company_facts

# Apple Inc. CIK = 320193
result = fetch_company_facts('320193')
print('Company:', result.get('company_name'))
print('CIK:', result.get('cik'))
print('Revenue:', result.get('revenue'))
print('Net Income:', result.get('net_income'))
"
```

**Expected:** JSON with `company_name`, `cik`, `revenue`, `net_income`, etc. No auth required.

---

## 3. Test Document

You need a PDF that contains financial data the LLM can extract (CIK, company name, revenue, etc.).

**Options:**

| Source | Description |
|--------|-------------|
| **SEC EDGAR** | Download a 10-K or 10-Q PDF from [sec.gov/edgar](https://www.sec.gov/edgar/searchedgar/companysearch.html). Search for a company (e.g., Apple), open a 10-K filing, and download the PDF. |
| **Earnings report** | Any PDF with a company name, CIK (or ticker), and financial figures. |
| **Sample** | Create a simple 1-page PDF with: "Apple Inc. CIK: 320193. Revenue: $383.3 billion. Net Income: $97.0 billion." |

**Example CIKs for testing:**
- Apple: `320193`
- Microsoft: `789019`
- Amazon: `1018724`

---

## 4. Manual End-to-End Flow

### Step 4.1: Upload via API

```bash
curl -X POST "http://localhost:8000/upload?user_id=1&audit_target=financial" \
  -F "files=@/path/to/your/financial-report.pdf"
```

**Expected response (202 Accepted):**
```json
{
  "task_ids": ["123"],
  "total_files": 1,
  "message": "Files queued for processing"
}
```

### Step 4.2: Poll Status

```bash
TASK_ID=123  # Use the task_id from upload response
curl "http://localhost:8000/status/${TASK_ID}"
```

Wait until `status` is `COMPLETED` or `PROCESSING` finishes. Check worker logs: `tail -f logs/sqs_worker.log`.

### Step 4.3: Inspect Result

```bash
curl "http://localhost:8000/result/${TASK_ID}"
```

**Check:**
- `audit_target` = `"financial"`
- `extracted_json` contains `cik`, `company_name`, `revenue`, `net_income`, etc.
- `api_response_json` contains SEC data (if CIK was valid)
- `verification_status` = `VERIFIED` or `DISCREPANCY_FLAG`

### Step 4.4: Database Check (Optional)

```bash
cd document-processor
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT id, document_id, audit_target, verification_status, 
         extracted_json->>'cik' as cik,
         extracted_json->>'company_name' as company_name
  FROM audit_logs 
  WHERE audit_target = 'financial' 
  ORDER BY created_at DESC 
  LIMIT 5;
"
```

---

## 5. Frontend Testing

1. Open **http://localhost:3000**
2. Go to **Upload**
3. Select **"Financial (SEC / Stock Market)"** from the Audit Target dropdown
4. Upload a financial PDF
5. Wait for processing
6. Go to **Verification** or **Audit Log**
7. Confirm the document appears with `audit_target` = "Financial (SEC)"
8. Open a checkpoint and verify the discrepancy table shows Document Value vs API Value

---

## 6. Verification Outcomes

| Scenario | Expected |
|----------|----------|
| **Extraction finds CIK + matches SEC** | `VERIFIED` |
| **Extraction finds CIK, numbers differ >1%** | `DISCREPANCY_FLAG` with revenue/net_income/etc. flagged |
| **Extraction finds invalid CIK** | `DISCREPANCY_FLAG` (API unavailable) |
| **Document has no CIK** | Extraction may fail or return empty; API returns None → `DISCREPANCY_FLAG` |

---

## 7. Troubleshooting

| Issue | Check |
|-------|-------|
| **Upload returns 400 "Invalid audit_target"** | Ensure `financial` is in `AuditTarget` enum and `validate_audit_target` allows it |
| **Worker doesn't process** | SQS worker running? Check `logs/sqs_worker.log` |
| **extracted_json empty or missing cik** | Document may not contain CIK; try a 10-K PDF. Check `OPENAI_API_KEY` and extraction logs |
| **api_response_json null** | CIK invalid or SEC rate limit. Test `fetch_company_facts(cik)` standalone |
| **Frontend doesn't show Financial option** | Rebuild frontend; check `types/audit-target.ts` |

---

## 8. Quick Smoke Test

Minimal test without a real PDF (verification + API only):

```bash
cd document-processor

# 1. Verification logic
python -c "
from app.verification import verify_extraction
r = verify_extraction('financial', 
  {'cik':'320193','company_name':'Apple Inc.','revenue':'383285000000'},
  {'cik':'320193','company_name':'Apple Inc.','revenue':383285000000})
print('Status:', r.status)
assert r.status == 'VERIFIED'
print('OK')
"

# 2. SEC API
python -c "
from app.clients.sec_edgar import fetch_company_facts
r = fetch_company_facts('320193')
print('Company:', r.get('company_name'))
print('OK' if r else 'FAIL')
"
```

Both should print `OK`.
