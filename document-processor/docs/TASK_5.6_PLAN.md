# Task 5.6 — Implementation Plan

**Request Client Remediation: templated email; AWAITING_CLIENT_REMEDIATION state; upload flow to attach new doc and resume**

---

## Objective

Complete the Request Client Remediation flow with:

1. **Templated email** — Generate a draft email for the officer to send to the client
2. **AWAITING_CLIENT_REMEDIATION state** — Already implemented (Task 5.2)
3. **Upload flow to attach new doc and resume** — Allow client to upload a replacement document that re-runs the pipeline for the same checkpoint

---

## Current State

| Component | Status |
|-----------|--------|
| `POST /hitl/request-client-remediation` | ✅ Done (Task 5.2) — sets status to AWAITING_CLIENT_REMEDIATION |
| Templated email generation | ❌ Not implemented |
| Remediation upload (attach new doc) | ❌ Not implemented |
| Resume pipeline for remediation | ❌ Not implemented |

---

## Design Decisions

### 1. Templated Email

- **Purpose:** Officer sends a professional email to the client requesting corrected documents
- **Input:** Checkpoint context (discrepancy_flags, audit_target, filename, optional officer message)
- **Output:** `{subject: str, body: str}` — draft for officer to copy/edit and send
- **Delivery:** Email is **generated only** — no SMTP/SES. Officer copies from UI or API response
- **Templates:** One template per audit_target with placeholders for discrepancy details

### 2. Remediation Upload Strategy

- **Approach:** Extend `POST /upload` with optional `remediation_for_checkpoint_id` query param
- **When set:** Single file only; validate checkpoint exists, status=AWAITING_CLIENT_REMEDIATION, user owns document
- **Action:** Update existing Document with new s3_key and filename; set status=PENDING; re-queue to SQS with same task_id
- **No new Document:** Keeps audit trail clean; same document ID throughout lifecycle

### 3. Resume Flow

- **Worker:** No changes. Worker receives SQS message with task_id, s3_key, filename — processes as normal
- **Pipeline:** Full re-run from burst_pdf → extract → API → verify → persist or human_review
- **Result:** Either VERIFIED (COMPLETED) or DISCREPANCY_FLAG (PENDING_HUMAN_REVIEW again)

---

## Implementation Plan

### Step 1: Add Remediation Email Service

**File:** `app/remediation_email_service.py` (new)

**Function:** `generate_remediation_email(checkpoint_id: str, officer_message: str | None = None) -> dict[str, str]`

**Logic:**
1. Load Document by checkpoint_id; validate it exists
2. Get latest AuditLog for document (extracted_json, discrepancy_flags, audit_target) — join or subquery by max(id) per document_id
3. Select template by audit_target (epc, companies_house, hm_land_registry)
4. Fill placeholders: `{filename}`, `{discrepancy_summary}`, `{officer_message}`, `{audit_target}`
5. Return `{"subject": "...", "body": "..."}`

**Template structure (example for EPC):**
```
Subject: Action Required: Document Verification — {filename}

Dear Client,

Our verification process has identified discrepancies in the document you provided: {filename}.

{discrepancy_summary}

{officer_message}

Please upload a corrected document that addresses the issues above. You may reply to this email with the updated file attached, or use the upload link provided by your compliance officer.

Thank you,
Compliance Team
```

**Discrepancy summary:** Format discrepancy_flags as bullet list, e.g. "• property_address: extracted 'X' does not match registry 'Y'"

---

### Step 2: Extend Request Client Remediation Response

**File:** `app/schemas_hitl.py`

Add `RemediationEmailDraft` and extend response:

```python
class RemediationEmailDraft(BaseModel):
    subject: str
    body: str

class RequestClientRemediationResponse(BaseModel):
    success: bool = True
    message: str = ""
    task_id: Optional[str] = None
    status: Optional[str] = None
    email_draft: Optional[RemediationEmailDraft] = None  # NEW
```

**File:** `app/hitl_service.py`

In `apply_request_client_remediation()`:
- After setting status, call `generate_remediation_email(checkpoint_id, message)`
- Include `email_draft` in return dict

**File:** `app/main.py`

- Use `RequestClientRemediationResponse` for `POST /hitl/request-client-remediation` (or keep HITLResponse and add optional email_draft field)
- Simpler: add `email_draft` to HITLResponse as optional field

---

### Step 3: Add Optional Endpoint to Preview Email

**File:** `app/main.py`

`GET /hitl/remediation-email/{checkpoint_id}?message=...`

- Returns `RemediationEmailDraft` for preview before officer confirms Request Client Remediation
- Validates checkpoint exists and is PENDING_HUMAN_REVIEW

---

### Step 4: Extend Upload Endpoint for Remediation

**File:** `app/main.py`

Add query param to `POST /upload`:

```python
remediation_for_checkpoint_id: Optional[str] = None  # When set, attach file to existing checkpoint
```

**Constraints when `remediation_for_checkpoint_id` is set:**
1. **Single file only** — `len(files) == 1`, else 400
2. **Checkpoint exists** — Document with id=checkpoint_id exists
3. **Status = AWAITING_CLIENT_REMEDIATION**
4. **Same user** — document.user_id == user_id (from query)

**Flow (remediation):**
1. Validate constraints above
2. Read file, upload to S3 with key `uploads/{checkpoint_id}_remediation_{uuid}{ext}`
3. **Update** existing Document (id=checkpoint_id):
   - `s3_key` = new key
   - `filename` = new filename
   - `status` = "PENDING"
   - `error_message` = clear or truncate remediation note (optional: keep for audit)
   - `completed_at` = None, `result_text` = None (will be repopulated by worker)
4. Update Redis `task:{checkpoint_id}`: s3_key, filename, status=PENDING, progress=0, error="", completed_at=""
5. Send SQS message: `task_id=checkpoint_id`, new s3_key, new filename, audit_target from document
6. Return `UploadResponse(task_ids=[checkpoint_id], total_files=1, message="Remediation file queued for processing")`

**No new Document created.** Same task_id returned.

---

### Step 5: Add Remediation Validation Helper

**File:** `app/hitl_service.py`

**Function:** `validate_remediation_upload(checkpoint_id: str, user_id: int) -> Document`

- Query Document by id=checkpoint_id
- Raise ValueError if not found, status != AWAITING_CLIENT_REMEDIATION, or user_id != document.user_id
- Return document (for audit_target, etc.)

---

### Step 6: Update Upload Logic in main.py

**File:** `app/main.py`

In `upload_files`:

```python
# After rate limit / queue depth checks, before the for file in files loop:

remediation_checkpoint_id = remediation_for_checkpoint_id
if remediation_checkpoint_id:
    if len(files) != 1:
        raise HTTPException(400, "Remediation upload accepts exactly one file")
    # Validate and get document (sync call - use hitl_service)
    from app.hitl_service import validate_remediation_upload
    try:
        doc = validate_remediation_upload(remediation_checkpoint_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    validated_audit_target = doc.audit_target or "epc"
    # Skip normal audit_target validation from query
else:
    # Existing flow: validate audit_target from query
    ...
```

Then inside the loop, when `remediation_checkpoint_id`:
- Use checkpoint_id as task_id (no new Document)
- Upload to S3 with remediation key pattern
- Update Document via sync DB (use SessionLocal or inject sync session)
- Update Redis
- Send SQS
- Append task_id (checkpoint_id) to task_ids
- **Break after first file** (only one file in remediation mode)

For async/sync mixing: the upload endpoint uses `get_async_db`. For remediation we need to update Document. Options:
- Use `SessionLocal` directly in the remediation block (sync)
- Or add a sync helper that opens its own session

---

### Step 7: Handle Async/Sync in Upload

**Approach:** Use `SessionLocal` in the remediation block. The rest of the endpoint is async; the remediation block does a sync DB update. This is acceptable for a single update.

**Alternative:** Create `app/remediation_upload_service.py` with `process_remediation_upload(checkpoint_id, user_id, file_content, filename) -> str` that does all the work and returns task_id. Keeps main.py cleaner.

---

## Files to Create

| File | Purpose |
|------|---------|
| `app/remediation_email_service.py` | Generate templated email from checkpoint context |
| `app/remediation_upload_service.py` | Process remediation upload (validate, update doc, Redis, SQS) |

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/schemas_hitl.py` | Add `RemediationEmailDraft`; extend `HITLResponse` with optional `email_draft` |
| `app/hitl_service.py` | Call `generate_remediation_email` in `apply_request_client_remediation`; add `validate_remediation_upload` |
| `app/main.py` | Add `remediation_for_checkpoint_id` to upload; add `GET /hitl/remediation-email/{checkpoint_id}`; integrate remediation flow |

---

## Database

- **No migration required.** Reuse existing Document; update s3_key, filename, status in place.
- **Optional:** Add `remediation_uploaded_at` timestamp for analytics — out of scope for MVP.

---

## API Summary

| Endpoint | Change |
|----------|--------|
| `POST /hitl/request-client-remediation` | Response includes `email_draft: {subject, body}` |
| `GET /hitl/remediation-email/{checkpoint_id}` | New — preview email before applying |
| `POST /upload?remediation_for_checkpoint_id=123` | New param — attach file to checkpoint 123 and re-queue |

---

## Verification

| # | Test | Expected |
|---|------|----------|
| 1 | POST request-client-remediation | Response includes email_draft with subject and body |
| 2 | GET remediation-email/123 | Returns draft for checkpoint 123 (PENDING_HUMAN_REVIEW) |
| 3 | GET remediation-email/999 (wrong status) | 400 |
| 4 | POST upload with remediation_for=123, 1 file | Document 123 updated, SQS message sent, returns task_ids=[123] |
| 5 | POST upload with remediation_for=123, 2 files | 400 "Remediation upload accepts exactly one file" |
| 6 | POST upload with remediation_for=999 (not AWAITING_CLIENT_REMEDIATION) | 400 |
| 7 | Worker processes remediation task | Full pipeline runs; VERIFIED or PENDING_HUMAN_REVIEW |

---

## Out of Scope

- Sending email via SMTP/SES (officer copies draft manually)
- Client-facing upload portal (API supports it; UI in Phase 6)
- Deleting old S3 file when remediation uploads (orphaned file remains; Phase 7 retention policy may cover)
- Multi-file remediation (one file per remediation)

---

## Checklist Before Implementation

- [ ] Plan reviewed and approved
- [ ] Officer workflow: Request Remediation → copy email → send to client → client uploads via API or UI

---

**Ready for implementation. Say "start build" to implement.**
