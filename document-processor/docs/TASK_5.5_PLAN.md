# Task 5.5 — Implementation Plan

**Checkpoint TTL: expire checkpoints older than 7 days; exclude AWAITING_CLIENT_REMEDIATION**

---

## Objective

Automatically expire documents that have been in `PENDING_HUMAN_REVIEW` for more than 7 days. Documents in `AWAITING_CLIENT_REMEDIATION` are **never** expired — they remain until the client uploads a new document or an officer takes action.

---

## Rationale

| Status | TTL Applied? | Reason |
|--------|--------------|--------|
| `PENDING_HUMAN_REVIEW` | Yes (7 days) | Stale queue; encourage timely officer action |
| `AWAITING_CLIENT_REMEDIATION` | No | Waiting on external client; may take weeks/months |

---

## Design Decisions

### 1. Expiration Target

- **Status:** Only `PENDING_HUMAN_REVIEW`
- **Excluded:** `AWAITING_CLIENT_REMEDIATION` (never expired)

### 2. Age Calculation

- **Field:** `Document.completed_at` (when the document entered HITL)
- **Fallback:** If `completed_at` is null (edge case), use `Document.created_at`
- **Threshold:** 7 days (configurable via `HITL_CHECKPOINT_TTL_DAYS`)

### 3. Expired Status

- **New status:** `EXPIRED`
- **Meaning:** Document was in PENDING_HUMAN_REVIEW too long; no longer in active HITL queue
- **Effect:** Dropped from `GET /hitl/checkpoints` (already filters by status; EXPIRED not in list)

### 4. Execution Model

- **Approach:** Standalone script + cron (or systemd timer)
- **Rationale:** No new runtime dependencies; portable; can run on any host with DB access
- **Alternative:** Optional FastAPI startup background task (APScheduler) — out of scope for initial implementation

---

## Implementation Plan

### Step 1: Add Config Setting

**File:** `app/config.py`

Add:

```python
# HITL Checkpoint TTL (Task 5.5)
hitl_checkpoint_ttl_days: int = 7
```

Support env var `HITL_CHECKPOINT_TTL_DAYS` (default: 7).

---

### Step 2: Add `expire_hitl_checkpoints()` to hitl_service

**File:** `app/hitl_service.py`

**Function:** `expire_hitl_checkpoints() -> dict[str, Any]`

**Logic:**
1. Compute cutoff: `now - timedelta(days=settings.hitl_checkpoint_ttl_days)`
2. Query: `Document` where `status == 'PENDING_HUMAN_REVIEW'` and `(completed_at < cutoff OR (completed_at IS NULL AND created_at < cutoff))`
3. For each document:
   - Set `document.status = 'EXPIRED'`
   - Update Redis: `redis_client.hset(f"task:{task_id}", "status", "EXPIRED")`
4. Commit, close session
5. Return `{"expired_count": N, "message": "Expired N checkpoints"}`

**Dependencies:** `app.dependencies.redis_client`, `app.config.settings`, `datetime.timedelta`

---

### Step 3: Create Standalone Expiry Script

**File:** `scripts/expire_hitl_checkpoints.py` (new)

**Purpose:** Cron-callable script to run expiry job.

**Logic:**
1. Load app config (ensure `.env` is in path or `document-processor` root)
2. Call `expire_hitl_checkpoints()` from `app.hitl_service`
3. Log result (e.g. `Expired 3 checkpoints`)
4. Exit 0

**Usage:**
```bash
cd document-processor && python3 scripts/expire_hitl_checkpoints.py
```

**Cron example (daily at 2am):**
```
0 2 * * * cd /path/to/document-processor && python3 scripts/expire_hitl_checkpoints.py >> /var/log/expire_checkpoints.log 2>&1
```

---

### Step 4: Update list_hitl_checkpoints (No Change Required)

**File:** `app/hitl_service.py`

`list_hitl_checkpoints()` already filters by `status IN ('PENDING_HUMAN_REVIEW', 'AWAITING_CLIENT_REMEDIATION')`. Once documents are set to `EXPIRED`, they automatically drop out of the listing. **No code change.**

---

### Step 5: Update schemas_api.py

**File:** `app/schemas_api.py`

`TaskStatusResponse.status` uses `Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED", "PENDING_HUMAN_REVIEW", "AWAITING_CLIENT_REMEDIATION"]`. Add `"EXPIRED"` so `/status/{task_id}` and `/tasks` return valid responses for expired documents.

---

### Step 6: Optional Admin Endpoint (Recommended)

**File:** `app/main.py`

Add `POST /hitl/expire-checkpoints` (or `/internal/expire-checkpoints`) for manual trigger or cron-over-HTTP.

**Logic:**
- Call `expire_hitl_checkpoints()`
- Return `{"expired_count": N}`

**Security:** Consider protecting with API key or internal-only (e.g. X-Internal-Key header). For MVP, can be unprotected if deployed behind firewall; document in plan.

---

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/expire_hitl_checkpoints.py` | Cron-callable expiry script |

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/config.py` | Add `hitl_checkpoint_ttl_days` |
| `app/hitl_service.py` | Add `expire_hitl_checkpoints()` |
| `app/main.py` | Add `POST /hitl/expire-checkpoints` (optional) |
| `app/schemas_api.py` | Add `"EXPIRED"` to `TaskStatusResponse.status` Literal |

---

## Database

- **No migration required.** `Document.status` is `String(50)`; `EXPIRED` fits.
- **Index:** Existing `idx_user_status` on `(user_id, status)` supports queries. Optional: add `idx_documents_status_completed` for `(status, completed_at)` if expiry query is slow at scale.

---

## Verification

| # | Test | Expected |
|---|------|----------|
| 1 | Document in PENDING_HUMAN_REVIEW, completed_at 8 days ago | After run: status=EXPIRED, not in GET /hitl/checkpoints |
| 2 | Document in AWAITING_CLIENT_REMEDIATION, completed_at 30 days ago | After run: status unchanged, still in listing |
| 3 | Document in PENDING_HUMAN_REVIEW, completed_at 3 days ago | After run: status unchanged |
| 4 | Document with completed_at=NULL, created_at 10 days ago | After run: status=EXPIRED (fallback to created_at) |
| 5 | Redis task:{id} | After expiry: status=EXPIRED in Redis |

---

## Out of Scope

- APScheduler / in-process background job (can add later)
- Notification/alert when checkpoints are expired
- Configurable expiry action (e.g. FAILED vs EXPIRED)
- LangGraph checkpoint cleanup (keep for audit trail)

---

## Checklist Before Implementation

- [ ] Plan reviewed and approved
- [ ] Cron or scheduler available for production deployment

---

**Ready for implementation. Say "start build" to implement.**
