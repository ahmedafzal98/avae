# Course Project Proposal — Agentic AI

**Course ID:** 120055 — Agentic AI  

**Instructor:** Dr. Syed Farhan Mohsin  

---

## Group Information

| Name | Student ID |
|------|------------|
| Syeda Aliya Zaidi | 13604 |
| Ahmed Afzal | 13900 |
| Shahzaib | 64863 |

**Group size:** 3 members  

---

## Project Title

**AVAE — Agentic Verification and Audit Engine**

Enterprise-oriented document processing for UK-focused compliance workflows: PDFs are processed through an orchestrated **LangGraph** pipeline, structured fields are extracted with LLM (and optional vision paths), results are compared to official registry data where implemented, and discrepancies route to **human-in-the-loop (HITL)** checkpoints with audit logging. A separate **RAG chat** path answers questions over embedded document chunks stored in PostgreSQL.

*This proposal describes only what exists in the current codebase; no planned or speculative features are included.*

---

## 1. Abstract

The project is a full-stack application whose core backend is a **LangGraph** `StateGraph` compiled with an optional **PostgreSQL checkpointer** (`PostgresSaver`) for durable graph state. An **AWS SQS worker** pulls tasks and runs the graph end-to-end. The graph implements a fixed pipeline with **conditional edges**: after verification, documents either persist immediately or enter a **human review** node before persistence. The FastAPI service exposes upload, status, results, HITL actions, audit APIs, and document-scoped **RAG chat**. A **Next.js** dashboard (with **Clerk** authentication helpers in the frontend code) provides the primary UI; a **Streamlit** app in the repository calls the HTTP API for alternative demos.

---

## 2. Problem & Motivation (as implemented)

Organizations need to **extract structured data from PDFs**, **compare** it to authoritative registers where possible, and **record** outcomes for audit. The system addresses this by combining automated extraction (including OCR and vision-assisted chart handling), deterministic verification rules, explicit routing to human review when automated verification does not pass, and persistent audit records.

---

## 3. Agentic / Orchestration Design (actual implementation)

The orchestration is **not** a free-form multi-LLM “agent debate”; it is a **deterministic LangGraph workflow** with shared typed state (`AVAEState`) and named nodes.

**Graph structure (from `document-processor/app/graph/graph.py`):**

- **Entry:** `burst_pdf`  
- **Conditional:** `burst_pdf` → `classify_pages` or `handle_error` (on error)  
- **Linear:** `classify_pages` → `extract_parallel` → `merge_extractions` → `normalize` → `fetch_api` → `verify`  
- **Conditional:** `verify` → `persist` **or** `human_review` (via `route_hitl`)  
- **Linear:** `human_review` → `persist` → `END`  
- **Error:** `handle_error` → `END`  

**Execution:** `run_avae_graph` in `document-processor/app/graph/__init__.py` invokes the compiled graph with `config = {"configurable": {"thread_id": task_id}}` for checkpointing / HITL threading.

---

## 4. Pipeline Capabilities (by node)

| Stage | Behavior (from code) |
|--------|-------------------------|
| **burst_pdf** | Downloads PDF from **AWS S3**; uses **PyMuPDF** to burst pages (text + rasterized page images). |
| **classify_pages** | Heuristic labels per page: `text`, `image`, `table`, or `chart`. |
| **extract_parallel** | Per-page extraction in a **thread pool**; image pages: **Tesseract** (e.g. Arabic/multilingual) then **AWS Textract** fallback; chart pages: **VLM** (`extract_chart_summary`); otherwise PyMuPDF text. If per-page extraction yields nothing, **legacy extraction + LlamaParse** fallback. |
| **merge_extractions** | Concatenates per-page content with page headers. |
| **normalize** | **Structured LLM extraction** via `extract_structured` for the selected `audit_target`. If `audit_target == "vision_poc"`, uses **GPT-4o vision** on PDF bytes (`extract_structured_vision`) with text fallback. |
| **fetch_api** | Calls **Companies House** (`fetch_company` by `company_number`) or **HM Land Registry** (`fetch_land_data` by `property_address`) when `extracted_json` is present. For **`epc`**, the node currently sets `api_response` to **`None`** (no EPC HTTP call in this node). |
| **verify** | **Rule-based** comparison in `verification.py` (no LLM): statuses include **`VERIFIED`**, **`DISCREPANCY_FLAG`**, and **`EXTRACTED`** (e.g. financial / `vision_poc` when no external API response). |
| **route_hitl** | Routes to **`persist`** if status is `VERIFIED` or `EXTRACTED`; otherwise **`human_review`**. |
| **human_review** | Builds `hitl_checkpoint_id` and `document_preview` for review UI. |
| **persist** | Writes **audit logs**, updates **PostgreSQL** `Document`, caches result in **Redis**, cleans temp files. |
| **handle_error** | Marks task/document **FAILED** in Redis and PostgreSQL. |

**Supported `audit_target` values** (from `api_registry.py` / upload): include `companies_house`, `hm_land_registry`, `epc`, `financial`, and `vision_poc`.

---

## 5. Infrastructure & Tools in the Repository

- **API:** FastAPI (`document-processor/app/main.py`), documented at `/docs`.  
- **Queue & storage:** AWS **SQS** (worker loop), **S3** for PDFs.  
- **Cache / task state:** **Redis** (task hash, result TTL).  
- **Database:** **PostgreSQL** with **pgvector** for `document_chunks` embeddings.  
- **Worker:** `python -m app.sqs_worker` — invokes **`run_avae_graph`** per message (no Celery in this path; comments note Celery replaced by SQS).  
- **Local dev:** Root `start-dev.sh` initializes DB, runs **uvicorn** on port **8000**, SQS worker, and **Next.js** on port **3000** (expects Postgres on **5433** and Redis **6379** per script).  
- **RAG:** `rag_service.py` — **SentenceSplitter**-style chunking, **OpenAI `text-embedding-3-small`**, async **`ingest_document`** into pgvector. **`reprocess_documents.py`** in the repo calls `ingest_document` for (re)ingestion.  
- **Chat:** `POST /chat` uses **`ChatService`**: embed question → **cosine similarity** on `document_chunks` → optional use of stored **`Document.summary`** when scoped to a document → **OpenAI `gpt-4o`** answer with source chunk metadata.  
- **HITL REST:** Endpoints include checkpoint listing/summary, override, manual correction, request client remediation, remediation email draft, expire checkpoints (see `main.py` tags `HITL`).  
- **Audit REST:** List audit logs, stats, and detail by id.  
- **Frontend:** Next.js app with routes such as Dashboard, Upload, Verification (`/hitl`), Audit Log, Settings (`AppSidebar.tsx`).  
- **Auth (frontend):** Clerk (`useAuth`, `useUser`) for tokens and officer display.  
- **Optional UI:** `streamlit-frontend/streamlit_app.py` — HTTP client to a deployed API URL (configurable in file).

---

## 6. Limitations (faithful to code)

- **EPC:** The `fetch_api` node does not populate `api_response` for `epc`; verification behavior when API data is missing follows `verification.py` (e.g. discrepancy path when no API payload).  
- **Prompt field:** Graph accepts `prompt` on upload; `run_avae_graph` docstring notes summary generation is not implemented in the graph.  
- **Checkpointer:** Requires a **sync** PostgreSQL URL; async URLs log a warning and skip the checkpointer.  
- **RAG ingestion:** The SQS worker path shown in `sqs_worker.py` runs LangGraph only; **bulk chunk embedding** is via **`reprocess_documents.py`** / `rag_service`, not embedded in the same snippet as the graph completion step.

---

## 7. Course Alignment (Agentic AI)

The project demonstrates **goal-directed orchestration** (fixed graph with state), **tool use** (registry APIs, OCR/Textract/VLM, LLM structured extraction), **conditional control flow** (verification → persist vs HITL), **persistent execution state** (LangGraph Postgres saver when configured), and **human-in-the-loop** resolution—consistent with agentic-system themes taught in an Agentic AI course, as realized in this codebase.

---

## 8. Deliverables for Evaluation / Presentation

- Runnable stack per **`README.md`** / **`SETUP.md`** and **`start-dev.sh`**.  
- Live or recorded walkthrough of **upload → worker → graph → verification/HITL → audit**, plus **RAG chat** where chunks exist.  
- Architecture explanation referencing **LangGraph** graph definition and **AVAE** state fields.

---

## 9. Declaration

We confirm that this proposal accurately describes our project as it exists in the repository at the time of submission, that we will present the same system to the instructor, and that we will follow academic integrity policies.

**Date:** April 13, 2026  

---

*End of proposal.*
