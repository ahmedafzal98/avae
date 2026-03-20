# AVAE — Complete Plan, Phases & Modules

**Agentic Verification and Audit Engine**  
Zero hallucination • Enterprise-grade • Mathematically verifiable compliance

---

## 1. Blueprint (8 Steps)

| Step | Name | Description |
|------|------|--------------|
| 1 | **Ingestion & Queueing** | Next.js upload → S3 → SQS → Worker polls and hands to LangGraph |
| 2 | **Bursting & Routing** | PyMuPDF burst PDF into pages; classify and route to LlamaParse / Textract / VLM |
| 3 | **Parallel Extraction** | LlamaParse (Markdown), Textract (JSON), VLM (summaries) run in parallel |
| 4 | **Data Normalization** | Structured LLM + Pydantic schema → single clean JSON |
| 5 | **External API Fetch** | API Registry selects API; fetch ground truth from Companies House, Land Registry, etc. |
| 6 | **Deterministic Verification** | Hard-coded Python comparison; VERIFIED or DISCREPANCY_FLAG |
| 7 | **HITL** | VERIFIED → straight-through; DISCREPANCY_FLAG → pause, checkpoint, human review |
| 8 | **Database Insertion** | Audit log + pgvector chunks; SQS message completed |

---

## 2. Completion Assessment

| Metric | Value |
|--------|-------|
| **Overall completion** | ~25–30% |
| **Remaining work** | ~70–75% |

### By Step

| Step | Completion |
|------|-------------|
| 1. Ingestion & Queueing | ~75% |
| 2. Bursting & Routing | ~5% |
| 3. Parallel Extraction | ~10% |
| 4. Data Normalization | ~15% |
| 5. External API Fetch | 0% |
| 6. Deterministic Verification | 0% |
| 7. HITL | 0% |
| 8. Database Insertion | ~80% |

---

## 3. Phases

### Phase 1: Foundation (Weeks 1–2)

**Goal:** Audit target + structured extraction in pipeline

| # | Task |
|---|------|
| 1.1 | Add `audit_target` enum to upload API and SQS payload |
| 1.2 | Add `audit_target` to Document; create `audit_logs` table |
| 1.3 | Create schema registry (EPCExtraction, CorporateKYC, LandRegistry) |
| 1.4 | Integrate structured extraction into worker after LlamaParse; route by audit_target |
| 1.5 | Create API Registry mapping targets to API config |
| 1.6 | Design S3 retention policy (document for Phase 7 implementation) |

**Deliverable:** Upload with audit_target → LlamaParse → structured extraction → stored in audit_logs

---

### Phase 2: External APIs & Verification (Weeks 3–4)

**Goal:** Ground truth fetch + deterministic verification

| # | Task |
|---|------|
| 2.1 | Companies House client |
| 2.2 | HM Land Registry client |
| 2.3 | EPC Open Data client |
| 2.4 | Verification module: `verify_extraction()` → VERIFIED or DISCREPANCY_FLAG |
| 2.5 | Worker: after extraction → API call → verify → update audit_logs |

**Deliverable:** End-to-end: extraction → API fetch → verification → status in audit_logs

---

### Phase 3: LangGraph Orchestration (Weeks 5–6)

**Goal:** Replace linear worker with LangGraph + checkpointing

| # | Task |
|---|------|
| 3.1 | LangGraph graph: burst_pdf, classify_pages, extract_parallel, normalize, fetch_api, verify, route_hitl, persist |
| 3.2 | LangGraph PostgreSQL checkpointer (PostgresSaver creates `checkpoints`, `checkpoint_writes`) |
| 3.3 | SQS worker invokes LangGraph graph |
| 3.4 | Conditional routing: VERIFIED → persist; DISCREPANCY_FLAG → human_review |

**Deliverable:** LangGraph-driven pipeline with checkpointing and HITL routing

---

### Phase 4: Bursting & Multi-Tool Extraction (Weeks 7–8)

**Goal:** Page-level bursting and routing

| # | Task |
|---|------|
| 4.1 | PyMuPDF burst PDF into pages in memory |
| 4.2 | Page classifier (text vs image, table density, chart regions) |
| 4.3 | Textract integration for image-only pages |
| 4.4 | VLM integration for chart/graph regions |
| 4.5 | Parallel execution (asyncio.gather or concurrent.futures) |
| 4.6 | Merge step: combine Markdown + Textract JSON + VLM summaries before normalize |

**Deliverable:** Page-level routing and parallel extraction

---

### Phase 5: HITL & Checkpoint Resume (Weeks 9–10)

**Goal:** Human review and resume from checkpoints

| # | Task |
|---|------|
| 5.1 | HITL state model (checkpoint_id, discrepancies, document preview) |
| 5.2 | Override / Manual Correction / Request Client Remediation API endpoints |
| 5.3 | Resume logic: load checkpoint, inject human decision, continue graph to persist |
| 5.4 | Checkpoint listing endpoint for compliance officers |
| 5.5 | Checkpoint TTL (expire checkpoints older than 7 days; exclude AWAITING_CLIENT_REMEDIATION) |
| 5.6 | Request Client Remediation: templated email; AWAITING_CLIENT_REMEDIATION state; upload flow to attach new doc and resume |

**Deliverable:** Full HITL flow with Override, Manual Correction, and Request Client Remediation

---

### Phase 6: Next.js Frontend (Weeks 11–13)

**Goal:** Replace Streamlit with Next.js; integrate with backend

| # | Task |
|---|------|
| 6.1 | Next.js setup (App Router, Tailwind, auth) |
| 6.2 | Upload page with Audit Target selector |
| 6.3 | Status / results view (poll or WebSocket) |
| 6.4 | HITL dashboard: 50/50 split (document | discrepancy table); Override, Manual Correction, Request Client Remediation |
| 6.5 | Audit log view with filters |

**Frontend integration:** Phase 6. Backend APIs ready by end of Phase 5.

---

### Phase 7: Polish & Scale (Weeks 14–15)

| # | Task |
|---|------|
| 7.1 | Configure SQS DLQ and retry policy |
| 7.2 | Rate limiting for external APIs |
| 7.3 | Monitoring (verification pass rate, HITL volume, API latency) |
| 7.4 | Idempotency key on upload |
| 7.5 | Batch job entity for reporting |
| 7.6 | **Zero-Data Retention:** S3 Lifecycle Policy — automatically delete uploaded PDFs 24–48 hours after **workflow completion** (status = VERIFIED or COMPLETED). Critical for enterprise trust and compliance. Do not delete while processing or in HITL. |

---

### Phase 8: Semantic Memory (Weeks 16–17)

**Goal:** Adaptive agentic layer — learn from past HITL decisions and suggest remediations for similar audits

| # | Task |
|---|------|
| 8.1 | Create `override_memories` table: audit_target, discrepancy_type, justification, context_snapshot, embedding (pgvector), officer_id, created_at |
| 8.2 | On Override / Manual Correction: persist decision to override_memories with embedded context |
| 8.3 | Semantic Memory service: `get_similar_overrides(discrepancy_context, audit_target, k=5)` → similarity search via pgvector |
| 8.4 | HITL node: when checkpoint enters human_review, call `get_similar_overrides()` and attach suggestions to state |
| 8.5 | HITL dashboard: display "Similar past overrides" panel with one-click "Apply same" (officer still confirms) |
| 8.6 | Audit trail: log every suggestion shown and provenance (which override_memories IDs informed it) |
| 8.7 | Pilot with single audit target (e.g. EPC); validate before rolling out to all targets |

**Deliverable:** HITL suggestions powered by semantic memory; human always confirms — never autonomous application

**Design principles:**
- **Suggestions only** — system never auto-applies; officer retains full accountability
- **Full provenance** — every suggestion traceable to source override_memories
- **Narrow scope** — start with one audit target; expand after validation

---

## 4. Modules

### 4.1 Core Backend

| Module | Purpose |
|--------|---------|
| `app/main.py` | FastAPI app; upload, status, result, chat, audit endpoints |
| `app/config.py` | Settings; SQS DLQ, external API keys |
| `app/database.py` | SQLAlchemy engines; init_db |
| `app/db_models.py` | User, Document, DocumentChunk, AuditLog |

### 4.2 AVAE-Specific

| Module | Purpose |
|--------|---------|
| `app/api_registry.py` | Audit target → API config (base URL, ID field, auth, rate limit) |
| `app/schemas_extraction.py` | EPCExtraction, CorporateKYCExtraction, LandRegistryExtraction |
| `app/verification.py` | Deterministic compare; normalization; VERIFIED / DISCREPANCY_FLAG |
| `app/clients/companies_house.py` | Companies House REST API client |
| `app/clients/land_registry.py` | HM Land Registry API client |
| `app/clients/epc.py` | EPC Open Data API client |

### 4.3 Extraction

| Module | Purpose |
|--------|---------|
| `app/tasks.py` | LlamaParse extraction; legacy fallback |
| `app/extractors/textract_extractor.py` | AWS Textract for scanned pages |
| `app/extractors/vlm_extractor.py` | VLM for charts/graphs |

### 4.4 Orchestration (Phase 3+)

| Module | Purpose |
|--------|---------|
| `app/graph/state.py` | LangGraph state definition |
| `app/graph/nodes.py` | burst_pdf, classify_pages, extract_parallel, normalize, fetch_api, verify, persist |
| `app/graph/graph.py` | LangGraph workflow; conditional routing |
| `app/semantic_memory.py` | Override memory storage; `get_similar_overrides()`; pgvector similarity search |

### 4.5 Infrastructure

| Module | Purpose |
|--------|---------|
| `app/aws_services.py` | S3 and SQS operations |
| `app/sqs_worker.py` | SQS polling; invokes LangGraph or legacy pipeline |
| `app/rag_service.py` | Chunking, embeddings, pgvector storage |
| `app/chat_service.py` | RAG query + GPT-4 |

### 4.6 Frontend (Phase 6)

| Module | Purpose |
|--------|---------|
| Next.js app | App Router, Tailwind |
| Upload page | Audit Target selector; call `/upload` |
| Status / results | Poll or WebSocket |
| HITL dashboard | 50/50 split; Override, Manual Correction, Request Client Remediation; "Similar past overrides" panel (Phase 8) |
| Audit log view | List audits with filters |

---

## 5. Milestones

| Milestone | Phase | Week |
|-----------|-------|------|
| Audit target + structured extraction in pipeline | 1 | 2 |
| External API + deterministic verification | 2 | 4 |
| LangGraph orchestration + checkpointing | 3 | 6 |
| Page bursting + Textract + VLM | 4 | 8 |
| HITL Override / Manual Correction / Request Client Remediation | 5 | 10 |
| Next.js frontend live | 6 | 13 |
| Production hardening | 7 | 15 |
| Semantic Memory (HITL suggestions) | 8 | 17 |

---

## 6. Critical Path

```
Phase 1 (Foundation) → Phase 2 (APIs + Verification) → Phase 3 (LangGraph)
                                                              ↓
Phase 6 (Next.js) ← Phase 5 (HITL) ← Phase 4 (Bursting)
                                                              ↓
                                              Phase 8 (Semantic Memory)
```

---

## 7. Database Tables

### Business Tables (Application-Managed)

| Table | Purpose |
|-------|---------|
| `users` | API users |
| `documents` | Uploaded docs; status; audit_target |
| `document_chunks` | RAG chunks; embeddings (pgvector) |
| `audit_logs` | Extracted JSON; API response; verification status; discrepancy flags |
| `override_memories` | Past Override/Manual Correction decisions; context snapshot; embedding (pgvector); provenance for Semantic Memory |

### LangGraph Checkpoint Tables (LangGraph-Managed)

When you implement PostgresSaver in Phase 3, LangGraph automatically creates its own tables (typically `checkpoints` and `checkpoint_writes`). These are **not** modeled in SQLAlchemy — LangGraph manages them.

| Table | Purpose |
|-------|---------|
| `checkpoints` | LangGraph checkpoint state (graph state snapshots) |
| `checkpoint_writes` | Checkpoint write history |

**Migration safeguard:** Exclude these tables from destructive migrations and "drop all" scripts. They coexist with your business tables. Dropping them will lose HITL checkpoint state and break resume functionality.

---

## 8. Audit Targets

| Target | ID Field | External API |
|--------|----------|--------------|
| `epc` | reference_number | EPC Open Data |
| `companies_house` | company_number | Companies House |
| `hm_land_registry` | title_number | HM Land Registry |

---

## 9. Verification Statuses

| Status | Meaning |
|--------|---------|
| `VERIFIED` | All fields match; straight-through |
| `DISCREPANCY_FLAG` | Mismatch; pause for human review |
| `PENDING_HUMAN_REVIEW` | Checkpoint created; awaiting officer action |
| `AWAITING_CLIENT_REMEDIATION` | Request Client Remediation sent; paused until new document uploaded |

---

## 10. HITL Actions

| Action | Meaning |
|--------|---------|
| **Override** | Accept extracted value as-is (even if it doesn't match API). Officer accepts responsibility. |
| **Manual Correction** | Officer corrects the value; system re-runs verification. Use for typos, minor extraction errors. |
| **Request Client Remediation** | Source document is wrong; contact client to fix. Draft templated email (e.g., "Please provide an updated utility bill matching this address"); pause checkpoint indefinitely until new document is uploaded. True enterprise remediation. |
