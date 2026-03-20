# Task 1.1 — Implementation Plan

**Add `audit_target` enum to upload API and SQS payload**

---

## Objective

Ensure the upload API accepts and validates `audit_target`, stores it in the database, includes it in the SQS message, and that the worker receives and passes it through the pipeline.

---

## Current State (What Already Exists)

| Component | Status |
|-----------|--------|
| `app/api_registry.py` | `AuditTarget` enum exists (epc, companies_house, hm_land_registry) |
| `app/main.py` | `audit_target` query param exists; passed to Document and SQS |
| `app/db_models.py` | `Document.audit_target` column exists |
| `app/sqs_worker.py` | Reads `audit_target` from message; passes to `process_pdf_from_s3` |

**Gap:** No strict validation against the enum. Invalid values (e.g. `"xyz"`) may be accepted.

---

## Implementation Plan

### Step 1: Strengthen Enum Usage

**File:** `app/api_registry.py`

- Confirm `AuditTarget` enum has: `epc`, `companies_house`, `hm_land_registry`
- Add helper: `get_valid_audit_targets()` → list of valid string values for validation/error messages

---

### Step 2: Add Validation to Upload API

**File:** `app/main.py`

- Import `AuditTarget` from `api_registry`
- Before creating Document / sending to SQS:
  - If `audit_target` is provided: validate it is in `AuditTarget` (by value)
  - If invalid: return `400 Bad Request` with message: `"Invalid audit_target. Allowed: epc, companies_house, hm_land_registry"`
  - If not provided or empty: use `"epc"` as default
- Normalize: store and send the lowercase string value (e.g. `audit_target.value`)

---

### Step 3: Ensure SQS Payload Includes `audit_target`

**File:** `app/main.py`

- Verify the `sqs_message` dict includes `audit_target` with the validated value
- Already present; confirm it uses the validated/default value from Step 2

---

### Step 4: Ensure Worker Validates/Handles `audit_target`

**File:** `app/sqs_worker.py`

- When reading `audit_target` from message body: if missing or invalid, default to `"epc"`
- Log a warning if invalid value received (helps debug client bugs)
- Pass validated/default `audit_target` to `process_pdf_from_s3`

---

### Step 5: Update OpenAPI Documentation

**File:** `app/main.py`

- Add description to `audit_target` param: `"Audit target: epc, companies_house, hm_land_registry. Default: epc"`
- FastAPI will auto-include this in `/docs`

---

### Step 6: Verify Database Column Exists

**File:** `app/db_models.py`

- Confirm `Document.audit_target` exists and accepts string values
- If migration `003_audit_logs_and_audit_target.sql` not yet applied, document that it must be run

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/api_registry.py` | Add `get_valid_audit_targets()` helper (optional) |
| `app/main.py` | Validate `audit_target` against enum; return 400 if invalid; add param description |
| `app/sqs_worker.py` | Default invalid/missing `audit_target` to `"epc"`; optional warning log |

---

## Files to Verify (No Changes Expected)

| File | Check |
|------|-------|
| `app/db_models.py` | `audit_target` column present |
| `app/main.py` | `audit_target` in `sqs_message` |
| `app/sqs_worker.py` | `audit_target` read from body and passed to `process_pdf_from_s3` |

---

## Test Cases (Manual Verification)

| # | Test | Expected |
|---|------|----------|
| 1 | Upload with `audit_target=epc` | Success; document and SQS message have `epc` |
| 2 | Upload with `audit_target=companies_house` | Success; document and SQS message have `companies_house` |
| 3 | Upload without `audit_target` | Success; defaults to `epc` |
| 4 | Upload with `audit_target=invalid` | 400 Bad Request; error lists allowed values |
| 5 | Worker receives message with `audit_target` | Processes with correct audit_target; logs show it |

---

## Out of Scope (Later Phases)

- Worker does not yet use `audit_target` for schema selection or API routing (Phase 1.4)
- LangGraph integration (Phase 3)
- Structured extraction by audit_target (Phase 1.4)

---

## Checklist Before Implementation

- [ ] Migration `003_audit_logs_and_audit_target.sql` applied (or Document.audit_target exists)
- [ ] Plan reviewed and approved by you

---

---

## Implementation Complete

Task 1.1 has been implemented. Summary of changes:

| File | Changes |
|------|---------|
| `app/api_registry.py` | **Created** — AuditTarget enum, validate_audit_target(), get_valid_audit_targets() |
| `app/main.py` | audit_target param; validation; Document.audit_target; Redis task_data; SQS payload |
| `app/db_models.py` | Document.audit_target column |
| `app/sqs_worker.py` | Read audit_target from message; validate/default; pass to process_pdf_from_s3 |
| `migrations/003_add_audit_target.sql` | **Created** — ALTER TABLE documents ADD audit_target |

**To apply migration:** `psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -f migrations/003_add_audit_target.sql`
