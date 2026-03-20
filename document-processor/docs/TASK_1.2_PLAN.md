# Task 1.2 — Implementation Plan

**Add `audit_target` to Document; create `audit_logs` table**

---

## Objective

Ensure the `audit_logs` table exists to store verification pipeline output (extracted JSON, API response, verification status). The `audit_target` on Document is already done in Task 1.1.

---

## Current State

| Component | Status |
|-----------|--------|
| `Document.audit_target` | ✅ Done (Task 1.1) |
| Migration 003 (audit_target on documents) | ✅ Exists |
| `audit_logs` table | ❌ Not created |
| `AuditLog` ORM model | ❌ Not created |

---

## Implementation Plan

### Step 1: Add AuditLog Model to db_models.py

**File:** `app/db_models.py`

Add new `AuditLog` class with columns:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer, PK | Primary key |
| `document_id` | Integer, FK → documents.id | Links to document |
| `audit_target` | String(50) | epc, companies_house, hm_land_registry |
| `extracted_json` | JSON/JSONB | Structured extraction from LLM (Phase 1.4) |
| `api_response_json` | JSON/JSONB, nullable | API response (Phase 2) |
| `verification_status` | String(50) | VERIFIED, DISCREPANCY_FLAG, PENDING (Phase 2) |
| `discrepancy_flags` | JSON/JSONB, nullable | Error details when verification fails (Phase 2) |
| `fields_compared` | JSON/JSONB, nullable | Audit trail of field comparisons (Phase 2) |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

Add indexes: `document_id`, `verification_status`, `audit_target`.

Add `JSON` import from SQLAlchemy (or use `sqlalchemy.dialects.postgresql.JSONB` for PostgreSQL).

---

### Step 2: Add AuditLog Relationship to Document

**File:** `app/db_models.py`

In `Document` class, add:

- `audit_logs` relationship (one-to-many: one document can have one audit log per processing run; for Phase 1 we assume one log per document).

---

### Step 3: Create Migration for audit_logs Table

**File:** `migrations/004_create_audit_logs.sql`

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    audit_target VARCHAR(50) NOT NULL,
    extracted_json JSONB NOT NULL,
    api_response_json JSONB,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    discrepancy_flags JSONB,
    fields_compared JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_document_id ON audit_logs(document_id);
CREATE INDEX idx_audit_logs_verification_status ON audit_logs(verification_status);
CREATE INDEX idx_audit_logs_audit_target ON audit_logs(audit_target);
```

---

### Step 4: Register AuditLog in init_db

**File:** `app/database.py`

Update the import in `init_db()` to include `AuditLog` so `Base.metadata.create_all()` creates the table for fresh installs:

```python
from app.db_models import User, Document, DocumentChunk, AuditLog
```

---

### Step 5: Apply Migration for Existing Databases

For databases that already have `documents` but not `audit_logs`, run:

```bash
cd document-processor
docker-compose exec -T postgres psql -U docuser -d document_processor < migrations/004_create_audit_logs.sql
```

Or with local PostgreSQL:

```bash
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -f migrations/004_create_audit_logs.sql
```

---

## Files to Create

| File | Action |
|------|--------|
| `migrations/004_create_audit_logs.sql` | Create |

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/db_models.py` | Add AuditLog model; add relationship to Document |
| `app/database.py` | Import AuditLog in init_db |

---

## Out of Scope (Later Phases)

- **Phase 1.4:** Worker will INSERT into `audit_logs` after structured extraction.
- **Phase 2:** Worker will UPDATE `audit_logs` with `api_response_json`, `verification_status`, `discrepancy_flags`, `fields_compared`.

Task 1.2 only creates the table and model; no worker logic changes.

---

## Verification

| # | Check | Command / Action |
|---|-------|------------------|
| 1 | Table exists | `psql -c "\d audit_logs"` |
| 2 | App starts | `uvicorn app.main:app --reload` |
| 3 | init_db creates table | Restart app; check logs for success |

---

## Checklist Before Implementation

- [ ] Plan reviewed and approved
- [ ] Migration 003 already applied (audit_target on documents)

---

## Implementation Complete

Task 1.2 has been implemented. Summary of changes:

| File | Changes |
|------|---------|
| `app/db_models.py` | Added AuditLog model; added audit_logs relationship to Document |
| `app/database.py` | Import AuditLog in init_db |
| `migrations/004_create_audit_logs.sql` | **Created** — CREATE TABLE audit_logs with indexes |

**To apply migration (existing DB):**
```bash
cd document-processor
docker-compose exec -T postgres psql -U docuser -d document_processor < migrations/004_create_audit_logs.sql
```

**Or with local psql:**
```bash
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -f migrations/004_create_audit_logs.sql
```

**Fresh installs:** Restart the app; init_db will create the table automatically.
