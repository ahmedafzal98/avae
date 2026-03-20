# Task 1.4 — Implementation Plan

**Integrate structured extraction into worker; route by audit_target**

---

## Objective

After text extraction, run structured LLM extraction using the schema for the document's `audit_target`, and store the result in `audit_logs`.

---

## Current Worker Flow

1. Download PDF from S3
2. Extract text (legacy PyPDF2/pdfplumber)
3. Generate summary (if prompt provided)
4. Skip RAG
5. Extract metadata
6. Save to Redis + PostgreSQL (documents table)

---

## New Flow (Task 1.4)

1. Download PDF from S3
2. Extract text (legacy)
3. **→ NEW: Structured extraction (LLM + schema) → insert audit_log**
4. Generate summary (if prompt provided)
5. Skip RAG
6. Extract metadata
7. Save to Redis + PostgreSQL

---

## Implementation Plan

### Step 1: Create Structured Extraction Module

**File:** `app/extraction_service.py` (new)

**Function:** `extract_structured(text: str, audit_target: str) -> dict | None`

- **Input:** Raw text from PDF, audit_target string (epc, companies_house, hm_land_registry)
- **Output:** Dict of extracted fields, or None if extraction fails
- **Logic:**
  1. If text is empty or whitespace-only → return None
  2. Get schema via `get_extraction_schema(audit_target)`
  3. Initialize LangChain `ChatOpenAI(model="gpt-4o", temperature=0)`
  4. Use `llm.with_structured_output(schema)` for structured output
  5. Invoke with prompt: "Extract the compliance entities from this document:\n\n{text}"
  6. Return `result.model_dump()` as dict
  7. On any exception (including invalid audit_target, missing schema) → log error, return None

**Dependencies:** `langchain-openai` (add to requirements.txt), `settings.openai_api_key` from config

---

### Step 2: Add langchain-openai to requirements.txt

**File:** `requirements.txt`

Add `langchain-openai` if not already a transitive dependency. Check with `pip list | grep langchain`.

---

### Step 3: Integrate into sqs_worker.py

**File:** `app/sqs_worker.py`

**Location:** After Step 3 (text extraction), before Step 3.1 (summary)

**New block:**
1. Import `extract_structured` from extraction_service
2. Import `AuditLog` from db_models
3. Call `extracted = extract_structured(text, audit_target)`
4. If `extracted` is not None:
   - Open db session, create `AuditLog(document_id=int(task_id), audit_target=audit_target, extracted_json=extracted, verification_status="PENDING")`
   - Add to session, commit, close
   - Log success
5. If `extracted` is None:
   - Log warning (extraction skipped or failed)
   - Do not insert audit_log (only store successful extractions)

**Error handling:** If extraction_service raises, catch and log; do not fail the entire task. Document processing continues.

---

### Step 4: Guard for Missing OpenAI Key

**File:** `app/extraction_service.py`

At start of `extract_structured`, check `settings.openai_api_key`. If missing, log warning and return None immediately.

---

### Step 5: Truncate Text for LLM

**File:** `app/extraction_service.py`

LLMs have token limits. Truncate text to ~12,000 chars (or configurable) before sending to avoid token overflow. Use `text[:12000]` or similar.

---

## Files to Create

| File | Purpose |
|------|---------|
| `app/extraction_service.py` | Structured extraction via LLM + schema |

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/sqs_worker.py` | Import extraction_service, AuditLog; call extract_structured; insert AuditLog |
| `requirements.txt` | Add langchain-openai if needed |

---

## Prompt for LLM

```
Extract the compliance entities from this document. Return only the structured fields, no additional commentary.

Document text:
---
{text}
---
```

---

## Verification

| # | Test | Expected |
|---|------|----------|
| 1 | Upload EPC PDF with audit_target=epc | audit_logs has 1 row with extracted_json (reference_number, etc.) |
| 2 | Upload with audit_target=companies_house | audit_logs has row with company_number, company_name, etc. |
| 3 | OPENAI_API_KEY missing | Worker logs warning; no audit_log row; document still completes |
| 4 | Empty PDF (no text) | No audit_log row; no crash |

---

## Out of Scope

- Phase 2: API fetch and verification (will UPDATE audit_logs)
- LlamaParse re-enable (Phase 3)

---

## Checklist Before Implementation

- [ ] Plan reviewed and approved
- [ ] OPENAI_API_KEY in .env (required for extraction to run)

---

**Ready for your approval. Say "start build" to implement.**
