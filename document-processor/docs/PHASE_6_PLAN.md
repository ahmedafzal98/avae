# Phase 6 — Complete Implementation Plan

**Next.js Frontend: Replace Streamlit; integrate with AVAE backend**

---

## Objective

Build a Next.js frontend that replaces Streamlit and provides:

1. **Upload page** with Audit Target selector
2. **Status / results view** (poll or WebSocket)
3. **HITL dashboard** — 50/50 split (document | discrepancy table); Override, Manual Correction, Request Client Remediation
4. **Audit log view** with filters

---

## Prerequisites

- Backend running (FastAPI on port 8000)
- CORS enabled for frontend origin (backend already has `allow_origins=["*"]`)
- Node.js 18+ and npm

---

## Backend API Endpoints (Reference)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/upload` | POST | Upload PDF(s); params: `user_id`, `audit_target`, `remediation_for_checkpoint_id` (optional) |
| `/status/{task_id}` | GET | Task status |
| `/result/{task_id}` | GET | Extraction result (when COMPLETED) |
| `/tasks` | GET | List tasks (paginated) |
| `/hitl/checkpoints` | GET | List HITL checkpoints; params: `status`, `audit_target`, `page`, `page_size` |
| `/hitl/remediation-email/{checkpoint_id}` | GET | Preview remediation email |
| `/hitl/override` | POST | Override checkpoint |
| `/hitl/manual-correction` | POST | Manual correction |
| `/hitl/request-client-remediation` | POST | Request client remediation |
| `/hitl/expire-checkpoints` | POST | Expire old checkpoints |
| `/documents` | GET | List documents |
| `/users/login` | POST | Login or register |

---

## Implementation Plan

### Task 6.1: Next.js Setup (App Router, Tailwind, Auth)

**Goal:** Scaffold Next.js app with App Router, Tailwind, and simple auth.

**Steps:**

1. **Create Next.js app** (in `document-processor` or sibling `frontend/`):
   ```bash
   npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir
   cd frontend
   ```

2. **Project structure:**
   ```
   frontend/
   ├── src/
   │   ├── app/
   │   │   ├── layout.tsx
   │   │   ├── page.tsx
   │   │   ├── upload/page.tsx
   │   │   ├── tasks/page.tsx
   │   │   ├── hitl/page.tsx
   │   │   ├── audit/page.tsx
   │   │   └── login/page.tsx
   │   ├── components/
   │   │   ├── layout/
   │   │   ├── upload/
   │   │   ├── hitl/
   │   │   └── ...
   │   └── lib/
   │       ├── api.ts
   │       └── auth.ts
   ├── .env.local
   └── package.json
   ```

3. **Environment:**
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Auth (simple):**
   - Use `POST /users/login` with email
   - Store user in `sessionStorage` or React context
   - No password; email is identifier (matches backend)
   - Optional: `next-auth` for production

**Deliverable:** App runs; login page; navigation shell.

---

### Task 6.2: Upload Page with Audit Target Selector

**Goal:** Upload PDFs with audit_target selection.

**UI:**
- File input (drag & drop or click)
- Audit target dropdown: `epc` | `companies_house` | `hm_land_registry`
- Optional: User ID (default 1)
- Submit button
- Progress / success feedback

**API integration:**
```ts
POST /upload?user_id=1&audit_target=epc
Content-Type: multipart/form-data
files: File[]
```

**Response:** `{ task_ids: string[], total_files: number, message: string }`

**Remediation upload (optional on same page):**
- If `remediation_for_checkpoint_id` in URL/state: single file, show "Remediation upload" label

**Deliverable:** Upload page; files queued; task_ids returned.

---

### Task 6.3: Status / Results View (Poll or WebSocket)

**Goal:** View task status and results.

**UI:**
- List of tasks (from `GET /tasks` or `GET /documents`)
- Columns: filename, status, progress, created_at
- Status badges: PENDING, PROCESSING, COMPLETED, FAILED, PENDING_HUMAN_REVIEW, AWAITING_CLIENT_REMEDIATION
- Poll `GET /status/{task_id}` every 3–5s for active tasks
- "View result" button → opens result modal or `/result/{task_id}`

**API:**
- `GET /tasks?page=1&page_size=50`
- `GET /status/{task_id}` (poll every 3s for PENDING/PROCESSING)
- `GET /result/{task_id}` (when COMPLETED)

**Alternative:** WebSocket if backend adds it later; poll is sufficient for MVP.

**Deliverable:** Task list; status updates; result view.

---

### Task 6.4: HITL Dashboard (50/50 Split)

**Goal:** Compliance officer reviews checkpoints; Override, Manual Correction, Request Client Remediation.

**Layout: 50/50 split**
- **Left:** Document preview (filename, extracted_json, audit_target)
- **Right:** Discrepancy table (field, extracted, api, suggested_action)

**Data source:** `GET /hitl/checkpoints?status=&audit_target=&page=1&page_size=10`

**Actions (per checkpoint):**
1. **Override** — Button → `POST /hitl/override` with `{ checkpoint_id }`
2. **Manual Correction** — Form: field + corrections JSON → `POST /hitl/manual-correction`
3. **Request Client Remediation** — Modal: optional message → `POST /hitl/request-client-remediation` → show `email_draft` (copy to clipboard)

**Remediation preview:**
- `GET /hitl/remediation-email/{checkpoint_id}?message=...` for preview before applying

**Filtering:**
- Status: PENDING_HUMAN_REVIEW | AWAITING_CLIENT_REMEDIATION
- Audit target: epc | companies_house | hm_land_registry

**Pagination:** page, page_size

**Deliverable:** HITL dashboard; all three actions work; email draft copyable.

---

### Task 6.5: Audit Log View with Filters

**Goal:** List audit logs with filters.

**Backend:** May need new endpoint `GET /audit-logs` or use `GET /documents` + join. Check if backend has audit log listing.

**If no endpoint:** Add `GET /audit-logs` to backend:
- Query `AuditLog` with filters: `document_id`, `audit_target`, `verification_status`
- Paginate
- Return: id, document_id, document_id (filename), audit_target, verification_status, discrepancy_flags, created_at

**UI:**
- Table: document_id, filename, audit_target, verification_status, created_at
- Filters: audit_target, verification_status
- Expand row: show extracted_json, api_response, discrepancy_flags

**Deliverable:** Audit log list; filters; expand for details.

---

## File Structure (Summary)

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # Dashboard / landing
│   │   ├── login/page.tsx
│   │   ├── upload/page.tsx
│   │   ├── tasks/page.tsx
│   │   ├── hitl/page.tsx
│   │   └── audit/page.tsx
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── upload/
│   │   │   ├── FileUpload.tsx
│   │   │   └── AuditTargetSelect.tsx
│   │   ├── tasks/
│   │   │   ├── TaskList.tsx
│   │   │   └── TaskStatusBadge.tsx
│   │   ├── hitl/
│   │   │   ├── CheckpointList.tsx
│   │   │   ├── DocumentPreview.tsx
│   │   │   ├── DiscrepancyTable.tsx
│   │   │   └── HITLActions.tsx
│   │   └── audit/
│   │       └── AuditLogTable.tsx
│   └── lib/
│       ├── api.ts
│       └── auth.ts
├── .env.local
├── tailwind.config.ts
└── package.json
```

---

## API Client (`lib/api.ts`)

```ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function uploadFiles(files: File[], auditTarget: string, userId = 1) {
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  const res = await fetch(`${API_URL}/upload?user_id=${userId}&audit_target=${auditTarget}`, {
    method: 'POST',
    body: form,
  });
  return res.json();
}

export async function getCheckpoints(params?: { status?: string; audit_target?: string; page?: number }) {
  const q = new URLSearchParams(params as any).toString();
  const res = await fetch(`${API_URL}/hitl/checkpoints?${q}`);
  return res.json();
}

export async function hitlOverride(checkpointId: string) {
  const res = await fetch(`${API_URL}/hitl/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ checkpoint_id: checkpointId }),
  });
  return res.json();
}

// ... similar for manual-correction, request-client-remediation
```

---

## Suggested Implementation Order

| Order | Task | Est. Time | Dependency |
|-------|------|-----------|------------|
| 1 | 6.1 Next.js setup | 1–2 hrs | — |
| 2 | 6.2 Upload page | 2–3 hrs | 6.1 |
| 3 | 6.3 Status / results | 2–3 hrs | 6.1 |
| 4 | 6.4 HITL dashboard | 4–5 hrs | 6.1 |
| 5 | 6.5 Audit log | 2–3 hrs | 6.1, backend endpoint |

**Total:** ~12–16 hours

---

## Backend Gaps (If Any)

| Gap | Action |
|-----|--------|
| No `GET /audit-logs` | Add endpoint in `app/main.py`; query AuditLog with filters |
| CORS | Already `allow_origins=["*"]` — OK for dev |

---

## Verification Checklist

- [ ] Login with email
- [ ] Upload PDF with audit_target=epc
- [ ] Task list shows status; poll updates
- [ ] Task COMPLETED → view result
- [ ] HITL dashboard lists checkpoints
- [ ] Override → checkpoint disappears
- [ ] Request Client Remediation → email_draft shown; copy works
- [ ] Manual Correction → form submits; checkpoint resolved
- [ ] Audit log (if endpoint exists) → filters work

---

## Out of Scope (Phase 6)

- Phase 8 "Similar past overrides" panel (Phase 8)
- WebSocket (poll is sufficient)
- Production auth (NextAuth, OAuth)
- Remediation upload UI (can add later; API exists)

---

**Ready for implementation. Say "start build" to begin with Task 6.1.**
