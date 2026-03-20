# AVAE Frontend — Complete Plan, Phases & Modules

**Agentic Verification and Audit Engine — Next.js UI**  
Enterprise-grade • Banking-terminal aesthetic • Stitch design reference

---

## 1. Blueprint (8 Steps)

| Step | Name | Description |
|------|------|--------------|
| 1 | **Foundation & Scaffolding** | Next.js 15 (App Router), TypeScript, Tailwind CSS, ESLint; project structure |
| 2 | **Design System** | AVAE Sovereign Design System — colors, typography, components (shadcn/ui) |
| 3 | **Auth & Layout Shell** | Clerk (or Auth.js); sidebar navigation; protected routes |
| 4 | **Upload & Ingestion** | Drag-and-drop upload; Audit Target selector; Live Engine Status (SSE or poll) |
| 5 | **Verification Dashboard** | 50/50 split pane — PDF viewer (left) | discrepancy table (right); TanStack Table |
| 6 | **HITL Flow** | Override, Manual Correction, Request Client Remediation modals; justification ledger |
| 7 | **Audit Log & Filters** | Filterable audit table; status filters; date range; export |
| 8 | **Polish & Semantic Memory UI** | Accessibility pass; "Similar past overrides" panel (Phase 8 backend); animations |

---

## 2. Completion Assessment

| Metric | Value |
|--------|-------|
| **Overall completion** | 0% |
| **Remaining work** | 100% |

### By Step

| Step | Completion |
|------|------------|
| 1. Foundation & Scaffolding | 0% |
| 2. Design System | 0% |
| 3. Auth & Layout Shell | 0% |
| 4. Upload & Ingestion | 0% |
| 5. Verification Dashboard | 0% |
| 6. HITL Flow | 0% |
| 7. Audit Log & Filters | 0% |
| 8. Polish & Semantic Memory UI | 0% |

---

## 3. Technology Stack (Exact Tools)

### Core Framework

| Tool | Version | Purpose |
|------|---------|---------|
| **Next.js** | 15.x | App Router, SSR/ISR, API routes |
| **TypeScript** | 5.x | Type safety |
| **React** | 19.x | UI components |

### Styling & Components

| Tool | Purpose |
|------|---------|
| **Tailwind CSS** | 4.x | Utility-first styling, design tokens |
| **shadcn/ui** | Latest | Radix primitives, copy-paste components |
| **Radix UI** | (via shadcn) | Accessible Dialog, Tabs, Dropdown, etc. |
| **class-variance-authority (cva)** | (via shadcn) | Component variants |
| **tailwind-merge** | (via shadcn) | Class merging |

### State & Data

| Tool | Purpose |
|------|---------|
| **Zustand** | 5.x | Client state (UI, modals, split-pane) |
| **TanStack Query** | v5 | Server state, caching, mutations |
| **TanStack Table** | v8 | Headless tables for verification/audit |

### Real-Time Updates

| Approach | Use Case |
|----------|----------|
| **Server-Sent Events (SSE)** | Primary: job status, processing stages |
| **TanStack Query polling** | Fallback when SSE unavailable |

### Document Viewer

| Tool | Purpose |
|------|---------|
| **@react-pdf-viewer/core** | PDF rendering in left pane |
| **@react-pdf-viewer/default-layout** | Toolbar, zoom, page navigation |

### Authentication

| Tool | Purpose |
|------|---------|
| **Clerk** | Enterprise auth (SOC 2, GDPR, MFA, SSO) |
| **Auth.js** | Self-hosted alternative |

### Icons & Typography

| Tool | Purpose |
|------|---------|
| **Lucide React** | Icons (CheckCircle, AlertTriangle, ShieldCheck, etc.) |
| **Inter** | Primary UI font |
| **JetBrains Mono** or **Geist Mono** | Monospace for IDs, reference numbers |

### Animations

| Tool | Purpose |
|------|---------|
| **Motion** (Framer Motion) | Minimal: modal transitions, status changes |

---

## 4. Design Reference (Stitch Outputs)

The following screens from the **AVAE Sovereign Design System** (Stitch) define the target UI:

| Screen | Reference | Key Elements |
|--------|-----------|--------------|
| **Design System** | Image 1 | Primary #0F172A, Secondary #475569, Tertiary #059669 (verified), add Error #dc2626 (discrepancy); Inter typography; Primary/Secondary/Outlined buttons |
| **Ingestion Terminal** | Image 2 | Drag-and-drop zone; Audit Target dropdown; Verification Priority (Standard/Expedited); Live Engine Status panel |
| **HITL Modal** | Image 3 | Override / Request Client Remediation; Justification Ledger; Generate Email Draft; Cancel/Confirm |
| **Verification Dashboard** | Image 4 | 50/50 split; PDF viewer (zoom, pages); table: Field Name, Document Value, API Value, Status; VERIFIED/DISCREPANCY/PENDING badges |
| **Audit Log** | Image 5 | Filters: All, VERIFIED, DISCREPANCY_FLAG, PENDING_HUMAN_REVIEW; table; Audit Health Index; Pending Reconciliation |

---

## 5. Phases

### Phase 1: Foundation & Scaffolding (Week 1)

**Goal:** Next.js app with TypeScript, Tailwind, and project structure

| # | Task |
|---|------|
| 1.1 | Create Next.js 15 app: `npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir` |
| 1.2 | Configure `tailwind.config.ts` with design tokens (slate, emerald, rose) |
| 1.3 | Initialize shadcn/ui: `npx shadcn@latest init` |
| 1.4 | Install core deps: `zustand`, `@tanstack/react-query`, `@tanstack/react-table`, `lucide-react`, `motion` |
| 1.5 | Set up `NEXT_PUBLIC_API_URL` in `.env.local` |
| 1.6 | Create folder structure: `app/`, `components/`, `lib/`, `hooks/`, `stores/`, `types/` |

**Deliverable:** Next.js app runs; Tailwind + shadcn configured; folder structure in place

---

### Phase 2: Design System & Core Layout (Week 2)

**Goal:** AVAE Sovereign Design System; layout shell; sidebar navigation

| # | Task |
|---|------|
| 2.1 | Define CSS variables in `globals.css`: `--primary`, `--secondary`, `--tertiary` (emerald), `--destructive` (rose), `--muted`, `--background`, `--foreground` |
| 2.2 | Add Inter and JetBrains Mono via `next/font` |
| 2.3 | Add shadcn components: Button, Input, Select, Card, Table, Dialog, Tabs, Badge, DropdownMenu |
| 2.4 | Create `StatusBadge` component: VERIFIED (green), DISCREPANCY (red), PENDING (amber) |
| 2.5 | Build `AppSidebar`: AVAE Engine logo, "COMPLIANCE & AUDIT", nav items (Dashboard, Upload, Audit Log, Settings) |
| 2.6 | Build `AppHeader`: breadcrumb, user menu, Export/Share placeholders |
| 2.7 | Create root layout with sidebar + main content area |

**Deliverable:** Design system applied; sidebar + header; consistent typography and colors

---

### Phase 3: Auth & Protected Routes (Week 2–3)

**Goal:** Authentication; route protection; user context

| # | Task |
|---|------|
| 3.1 | Install Clerk: `npm install @clerk/nextjs` |
| 3.2 | Configure `ClerkProvider` in root layout; add `NEXT_PUBLIC_CLERK_*` env vars |
| 3.3 | Create `middleware.ts` for protected routes (`/upload`, `/hitl`, `/audit` require auth) |
| 3.4 | Build login/sign-up flow (Clerk components or custom) |
| 3.5 | Create `lib/api.ts`: base fetch wrapper with auth token injection |
| 3.6 | Optional: fallback to Auth.js if self-hosted auth preferred |

**Deliverable:** Auth works; protected routes redirect to login; API client injects token

---

### Phase 4: Upload & Ingestion Flow (Week 3–4)

**Goal:** Document upload; Audit Target selector; Live Engine Status

| # | Task |
|---|------|
| 4.1 | Build `UploadPage`: route `/upload` |
| 4.2 | Create `FileDropzone`: drag-and-drop zone; "Drop Verification Payload"; accept PDF, DOCX; max 250MB |
| 4.3 | Create `AuditTargetSelect`: dropdown (epc, companies_house, hm_land_registry) |
| 4.4 | Create `VerificationPriorityToggle`: Standard / Expedited |
| 4.5 | Integrate `POST /upload?user_id=&audit_target=`; handle `task_ids` response |
| 4.6 | Build `LiveEngineStatus` panel: Extracting → Querying Databases → Verifying → Upload Complete |
| 4.7 | Implement status updates: SSE endpoint `GET /status/stream/{task_id}` or poll `GET /status/{task_id}` every 3s via TanStack Query; **opt out of Next.js caching** for any status proxy routes (`dynamic = 'force-dynamic'`) — see §11.2 |
| 4.8 | Handle remediation upload: `remediation_for_checkpoint_id` query param; single-file mode |

**Deliverable:** Upload page; files queued; Live Engine Status updates in real time

---

### Phase 5: Verification Dashboard (Week 4–5)

**Goal:** 50/50 split pane; PDF viewer; discrepancy table

| # | Task |
|---|------|
| 5.1 | Build `VerificationDashboardPage`: route `/hitl` or `/verification` |
| 5.2 | Install `@react-pdf-viewer/core` and `@react-pdf-viewer/default-layout` |
| 5.3 | Create `DocumentPreview`: left pane; PDF viewer with zoom, page nav, search; **dynamic import with `next/dynamic` and `ssr: false`** to avoid blocking initial load (see §11.1) |
| 5.4 | Create `VerificationTable`: TanStack Table; columns: Field Name, Document Value, API Value, Status |
| 5.5 | Implement row styling: green for VERIFIED, red for DISCREPANCY, amber for PENDING |
| 5.6 | Add metrics header: Confidence Score, Verified Fields (14/16), Discrepancies (1) |
| 5.7 | Add actions: Export Report, Approve Entry, Re-run Extraction, Flag for Manual Review |
| 5.8 | Integrate `GET /hitl/checkpoints`; filter by status, audit_target; pagination |
| 5.9 | Ensure strict 50/50 split; responsive collapse to stacked on small screens |

**Deliverable:** Verification dashboard; PDF + table side-by-side; status-coded rows

---

### Phase 6: HITL Flow & Modals (Week 5–6)

**Goal:** Override, Manual Correction, Request Client Remediation; justification; email draft

| # | Task |
|---|------|
| 6.1 | Create `HITLModal`: triggered when user clicks discrepancy row or "Resolve" |
| 6.2 | Modal content: error title (e.g. "VALIDATION ERROR - CRN 0842"); discrepancy description |
| 6.3 | Add **Override** option: "Force verification based on internal evidence"; Justification Ledger textarea (required, 500 char max) |
| 6.4 | Add **Manual Correction** option: editable field for corrected value; submit re-runs verification |
| 6.5 | Add **Request Client Remediation** option: "Generate Email Draft" button; display templated email; copy to clipboard |
| 6.6 | Integrate `POST /hitl/override`, `POST /hitl/manual-correction`, `POST /hitl/request-client-remediation` |
| 6.7 | Integrate `GET /hitl/remediation-email/{checkpoint_id}` for preview |
| 6.8 | Add footer: Cancel, Confirm; show "AUTHORIZED AS [Officer Level]" |
| 6.9 | Use shadcn Dialog; Motion for open/close animation |

**Deliverable:** Full HITL flow; all three actions work; modal matches Stitch design

---

### Phase 7: Audit Log & Filters (Week 6–7)

**Goal:** Audit log table; filters; date range; export

| # | Task |
|---|------|
| 7.1 | Build `AuditLogPage`: route `/audit` |
| 7.2 | Create `AuditLogTable`: TanStack Table; columns: Date/Timestamp, Document ID, Audit Target, Verification Status, Actions |
| 7.3 | Add status filters: All Entries, VERIFIED, DISCREPANCY_FLAG, PENDING_HUMAN_REVIEW |
| 7.4 | Add date range: Last 7 Days, 30 Days, 90 Days, Custom Range |
| 7.5 | Add search: "Search audit trails..." |
| 7.6 | Integrate `GET /audit-logs` (or equivalent); pagination |
| 7.7 | Build `AuditHealthIndex` card: global verification success rate; trend indicator |
| 7.8 | Build `PendingReconciliation` card: Priority Discrepancies count; Unassigned Reviewers; "Resolve Queues" button |
| 7.9 | Add Export Report; expand row for full audit details |

**Deliverable:** Audit log with filters; health index; pending reconciliation

---

### Phase 8: Polish & Semantic Memory UI (Week 7–8)

**Goal:** Accessibility; "Similar past overrides" panel; animations; production readiness

| # | Task |
|---|------|
| 8.1 | WCAG audit: contrast (4.5:1 body text); focus rings; aria-labels; keyboard nav |
| 8.2 | Add "Similar past overrides" panel to HITL dashboard (requires Phase 8 backend) |
| 8.3 | Display `get_similar_overrides()` results; "Apply same" button (officer confirms) |
| 8.4 | Add provenance: which override_memories IDs informed each suggestion |
| 8.5 | Refine animations: modal transitions (150–200ms); status badge transitions; no decorative motion |
| 8.6 | Add loading skeletons for tables and modals |
| 8.7 | Error boundaries; toast notifications for API errors |
| 8.8 | Responsive polish: mobile/tablet layouts |
| 8.9 | Production env: `NEXT_PUBLIC_API_URL` for production backend |

**Deliverable:** Accessible; Semantic Memory panel (when backend ready); polished UX

---

## 6. Modules (File Structure)

### 6.1 App Routes

| Path | Purpose |
|------|---------|
| `src/app/layout.tsx` | Root layout; providers (Query, Clerk) |
| `src/app/page.tsx` | Dashboard / landing |
| `src/app/login/[[...login]]/page.tsx` | Clerk sign-in (if custom) |
| `src/app/upload/page.tsx` | Ingestion terminal |
| `src/app/verification/page.tsx` | Verification dashboard (50/50) |
| `src/app/audit/page.tsx` | Audit log |
| `src/app/settings/page.tsx` | Settings placeholder |

### 6.2 Components

| Component | Purpose |
|-----------|---------|
| `components/layout/AppSidebar.tsx` | AVAE Engine nav; Dashboard, Upload, Audit Log, Settings |
| `components/layout/AppHeader.tsx` | Breadcrumb; user menu; Export/Share |
| `components/ui/*` | shadcn components |
| `components/upload/FileDropzone.tsx` | Drag-and-drop upload |
| `components/upload/AuditTargetSelect.tsx` | Audit target dropdown |
| `components/upload/VerificationPriorityToggle.tsx` | Standard / Expedited |
| `components/upload/LiveEngineStatus.tsx` | Processing stages |
| `components/verification/DocumentPreview.tsx` | PDF viewer (left pane) |
| `components/verification/VerificationTable.tsx` | Discrepancy table (right pane) |
| `components/verification/StatusBadge.tsx` | VERIFIED / DISCREPANCY / PENDING |
| `components/hitl/HITLModal.tsx` | Override, Manual Correction, Request Remediation |
| `components/hitl/JustificationLedger.tsx` | Required textarea |
| `components/hitl/SimilarOverridesPanel.tsx` | Phase 8: past override suggestions |
| `components/audit/AuditLogTable.tsx` | Filterable audit table |
| `components/audit/AuditHealthIndex.tsx` | Success rate card |
| `components/audit/PendingReconciliation.tsx` | Priority discrepancies; Resolve Queues |

### 6.3 Lib & Hooks

| Module | Purpose |
|--------|---------|
| `lib/api.ts` | API client; upload, status, checkpoints, HITL actions, audit logs |
| `lib/auth.ts` | Auth helpers (if not using Clerk exclusively) |
| `hooks/useUpload.ts` | Upload mutation; TanStack Query |
| `hooks/useCheckpoints.ts` | Checkpoints query; filters |
| `hooks/useStatusStream.ts` | SSE or poll for task status |
| `hooks/useAuditLogs.ts` | Audit logs query; filters |
| `stores/ui-store.ts` | Zustand: modal state, sidebar collapse, selected checkpoint |

### 6.4 Types

| Module | Purpose |
|--------|---------|
| `types/api.ts` | API response types; Task, Checkpoint, AuditLog, etc. |
| `types/audit-target.ts` | epc \| companies_house \| hm_land_registry |

---

## 7. Milestones

| Milestone | Phase | Week |
|-----------|-------|------|
| Next.js + Design System live | 1–2 | 2 |
| Auth + Layout shell | 3 | 3 |
| Upload + Live Engine Status | 4 | 4 |
| Verification Dashboard (50/50) | 5 | 5 |
| HITL flow complete | 6 | 6 |
| Audit Log + Filters | 7 | 7 |
| Polish + Semantic Memory UI | 8 | 8 |

---

## 8. Critical Path

```
Phase 1 (Foundation) → Phase 2 (Design System) → Phase 3 (Auth)
        ↓
Phase 4 (Upload) → Phase 5 (Verification) → Phase 6 (HITL)
        ↓
Phase 7 (Audit Log) → Phase 8 (Polish + Semantic Memory)
```

---

## 9. Backend API Endpoints (Reference)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/upload` | POST | Upload PDF(s); params: `user_id`, `audit_target`, `remediation_for_checkpoint_id` |
| `/status/{task_id}` | GET | Task status (poll) |
| `/status/stream/{task_id}` | GET | SSE stream (optional) |
| `/result/{task_id}` | GET | Extraction result |
| `/tasks` | GET | List tasks |
| `/hitl/checkpoints` | GET | List HITL checkpoints |
| `/hitl/override` | POST | Override checkpoint |
| `/hitl/manual-correction` | POST | Manual correction |
| `/hitl/request-client-remediation` | POST | Request client remediation |
| `/hitl/remediation-email/{checkpoint_id}` | GET | Preview remediation email |
| `/audit-logs` | GET | List audit logs (filters) |

---

## 10. Design Tokens (AVAE Sovereign)

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--primary` | #0F172A | #f8fafc | Primary actions; headings |
| `--secondary` | #475569 | #94a3b8 | Secondary text; borders |
| `--tertiary` | #059669 | #34d399 | Verified; success |
| `--destructive` | #dc2626 | #f87171 | Discrepancy; error |
| `--warning` | #d97706 | #fbbf24 | Pending |
| `--muted` | #f1f5f9 | #1e293b | Backgrounds |
| `--background` | #ffffff | #0f172a | Page background |
| `--foreground` | #0f172a | #f8fafc | Text |

---

## 11. Architectural Traps to Watch Out For

Even with an optimal stack, an enterprise environment introduces edge cases. Keep these in mind as you build:

### 11.1 PDF Viewer Weight

The `@react-pdf-viewer` library is powerful but **heavy**. When building the Verification Dashboard:

- **Always** dynamically import the viewer using `next/dynamic` with `ssr: false`
- Do **not** let the PDF rendering engine block the initial page load for the rest of the application
- Lazy-load the viewer only when the user navigates to the Verification Dashboard or selects a document

```tsx
// Correct: Dynamic import with SSR disabled
const DocumentPreview = dynamic(
  () => import('@/components/verification/DocumentPreview'),
  { ssr: false, loading: () => <DocumentPreviewSkeleton /> }
);
```

### 11.2 App Router Caching

Next.js 15 has **highly aggressive default caching**. Since Live Engine Status relies on real-time polling or SSE:

- Be meticulous about **opting out** of Next.js caching for real-time API routes
- If using Next.js API routes as a proxy to the backend, add `export const dynamic = 'force-dynamic'` to those route handlers
- For client-side polling (TanStack Query → FastAPI), the frontend fetches directly—but any Next.js middleware or route that touches status data must not cache
- **Danger:** Stale verification statuses can cause compliance officers to approve or reject based on outdated data—a critical risk in regulated environments

```tsx
// In app/api/status/[taskId]/route.ts (if proxying)
export const dynamic = 'force-dynamic';
export const revalidate = 0;
```

### 11.3 Clerk vs. Auth.js

| Consideration | Clerk | Auth.js |
|---------------|-------|---------|
| **Enterprise MFA/SSO** | Built-in; minimal config | Manual setup; more configuration |
| **SAML/SSO** | Effortless for financial clients | Significant manual configuration |
| **Vendor lock-in** | SaaS; data in Clerk's systems | Self-hosted; full control |
| **Compliance** | SOC 2, GDPR out of the box | DIY compliance documentation |

**Recommendation:** Use Clerk for speed and enterprise compliance. If vendor lock-in is a concern, document an Auth.js migration path early. Auth.js is a great self-hosted fallback, but enterprise SAML/SSO with it requires significantly more manual configuration.

---

## 12. Verification Checklist

- [ ] Next.js app runs; Tailwind + shadcn configured
- [ ] Design system: colors, typography, StatusBadge
- [ ] Auth: login; protected routes
- [ ] Upload: drag-and-drop; Audit Target; Live Engine Status
- [ ] Verification: 50/50 split; PDF viewer; discrepancy table
- [ ] HITL: Override, Manual Correction, Request Remediation
- [ ] Audit Log: filters; health index; export
- [ ] Accessibility: contrast; focus; keyboard nav
- [ ] Semantic Memory panel (when backend ready)
- [ ] **Traps avoided:** PDF viewer dynamically imported (§11.1); status routes uncached (§11.2); auth strategy documented (§11.3)

---

## 13. Out of Scope (Initial Release)

- WebSocket (SSE or poll sufficient)
- Dark mode (can add later)
- Batch upload UI beyond single dropzone
- Advanced PDF annotation/highlighting of extracted regions
- Multi-language (i18n)

---

**Ready for implementation. Aligns with backend Phase 5 completion (HITL APIs) and Phase 8 (Semantic Memory).**
