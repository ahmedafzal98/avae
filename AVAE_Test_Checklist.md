# AVAE — QA Test Matrix & Bug Tracker

**Instructions:** Go feature by feature. For each row: (1) ask Claude Code to trace the relevant code and flag likely failure points, (2) manually test the scenario yourself, (3) log the result immediately (don't wait till the end).

**Severity levels:** 🔴 Critical (crash/data loss/security) | 🟠 High (feature broken) | 🟡 Medium (annoying, workaround exists) | ⚪ Low (cosmetic)

---

## 1. Authentication & Access

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 1.1 | Dev-mode bypass works | Load frontend with `NEXT_PUBLIC_DEV_SKIP_AUTH=true` | Lands on dashboard, no login wall | ☐ | | |
| 1.2 | No route accidentally protected/unprotected | Visit every page directly by URL | Consistent access behavior | ☐ | | |
| 1.3 | API without auth header | Call backend endpoints directly (curl/Postman) | Confirm what's actually enforced vs open | ☐ | | |

## 2. Document Upload

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 2.1 | Upload single valid PDF | Upload a normal English PDF | Success, appears in document list | ☐ | | |
| 2.2 | Upload bilingual (Arabic+English) PDF | Use sample from `samples/demo/` | Extracts both languages correctly | ☐ | | |
| 2.3 | Upload multiple files at once | Select 3-5 files together | All queue and process independently | ☐ | | |
| 2.4 | Upload oversized file | File larger than `MAX_FILE_SIZE_MB` | Clear error message, no crash | ☐ | | |
| 2.5 | Upload wrong file type | Upload .docx/.jpg/.zip etc. | Graceful rejection with clear message | ☐ | | |
| 2.6 | Upload corrupt/empty PDF | 0-byte file or broken PDF | Fails gracefully, doesn't hang queue | ☐ | | |
| 2.7 | Upload during high load | Upload while another doc is processing | No queue blocking, both process | ☐ | | |
| 2.8 | Cancel/retry upload | Start upload, refresh page mid-way | No orphaned/stuck records | ☐ | | |

## 3. Document Processing Pipeline

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 3.1 | Textract extraction (primary path) | Upload standard document | Text extracted correctly | ☐ | | |
| 3.2 | LlamaParse fallback triggers correctly | Simulate Textract failure/unsupported doc | Falls back cleanly, no data loss | ☐ | | |
| 3.3 | Tesseract fallback | Test local OCR path | ⚠️ Known broken in container — confirm status | ☐ | 🟠 | Already flagged as pending |
| 3.4 | SQS worker picks up jobs | Upload doc, watch queue depth via `/health` | Queue depth increases then drains to 0 | ☐ | | |
| 3.5 | Failed job goes to DLQ | Force a processing failure | Message lands in `pdf-processing-dlq` | ☐ | | |
| 3.6 | Worker recovers after crash | Kill worker process mid-job, restart | Job resumes/retries, not lost silently | ☐ | | |
| 3.7 | Processing status updates live | Watch document status field during processing | Status transitions visible (queued → processing → done) | ☐ | | |

## 4. Verification Modules

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 4.1 | Companies House verification — match | Doc with valid, real company number | Correct match returned | ☐ | | |
| 4.2 | Companies House — no match | Doc with fake/invalid company number | Clear "not found" handling, no crash | ☐ | | |
| 4.3 | Companies House — API down/rate-limited | Simulate API timeout | Graceful degradation, doesn't block whole pipeline | ☐ | | |
| 4.4 | EPC verification — match | Valid EPC document (e.g. sample PDF) | Correct energy rating data extracted | ☐ | | |
| 4.5 | EPC — no record found | Address with no EPC on file | Handled cleanly | ☐ | | |
| 4.6 | Land Registry verification | If implemented — test with real property data | Correct ownership data returned | ☐ | | |
| 4.7 | SEC EDGAR (financial vertical, if active) | Test if this path is actually wired to UI | Confirm whether it's live or dormant code | ☐ | | |
| 4.8 | Multiple verification sources on one doc | Doc that should hit 2+ verification sources | All results shown together correctly | ☐ | | |

## 5. RAG / Chat / AI Extraction

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 5.1 | Chat query about uploaded document | Ask a question referencing an uploaded doc | Relevant, accurate answer with source | ☐ | | |
| 5.2 | Chat query with no relevant context | Ask something unrelated to any document | Model doesn't hallucinate an answer | ☐ | | |
| 5.3 | Cross-document query | Ask a question spanning 2+ documents | Correctly pulls from multiple sources | ☐ | | |
| 5.4 | OpenAI API failure/timeout | Simulate API key issue or rate limit | Clear error, not a silent hang | ☐ | | |

## 6. Human-in-the-Loop (HITL)

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 6.1 | Checkpoint appears when expected | Trigger a low-confidence extraction | Shows up in `/hitl/checkpoints` | ☐ | | |
| 6.2 | Override a checkpoint | Manually correct/approve a flagged item | Saves correctly, reflected in document | ☐ | | |
| 6.3 | Checkpoint summary counts are accurate | Compare `/hitl/checkpoints/summary` to actual list | Numbers match reality | ☐ | | |
| 6.4 | Postgres checkpointer survives restart | Restart backend mid-review | HITL state not lost | ☐ | | |

## 7. Audit Trail

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 7.1 | Every action gets logged | Upload, verify, override — check audit log after each | All actions appear in `/audit-logs` | ☐ | | |
| 7.2 | Audit log detail view accurate | Open a specific audit log entry | Details match what actually happened | ☐ | | |
| 7.3 | Audit stats correct | Check `/audit-logs/stats` after known set of actions | Counts/numbers are accurate | ☐ | | |
| 7.4 | Audit logs are immutable | Try to see if logs can be edited/deleted via API | Should not be editable | ☐ | 🔴 | Important for compliance credibility |

## 8. Dashboard / General UI

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 8.1 | Document list loads and paginates | Load documents page with 20+ docs | Pagination works, no lag | ☐ | | |
| 8.2 | Filtering by status works | Filter by COMPLETED/PENDING/FAILED | Correct subset shown | ☐ | | |
| 8.3 | Document detail/PDF view | Open a processed document | PDF renders, verification data shown | ☐ | | |
| 8.4 | Loading states | Slow network (throttle in devtools) | Spinners/skeletons shown, not blank screen | ☐ | | |
| 8.5 | Error states are user-friendly | Force an API error | Clean message, not raw stack trace | ☐ | | |
| 8.6 | Mobile/responsive layout | Resize browser / test on phone | Usable, not broken layout | ☐ | | |
| 8.7 | Cross-browser check | Test on Chrome, Safari, Firefox | Consistent behavior | ☐ | | |

## 9. Infrastructure / Non-Functional

| # | Test Case | Steps | Expected | Result | Severity | Notes |
|---|---|---|---|---|---|---|
| 9.1 | `/health` endpoint accurate | Check during normal + high load | Correctly reflects redis/queue state | ☐ | | |
| 9.2 | CORS from production Vercel domain | Test all frontend→backend calls in production | No CORS errors | ☐ | | |
| 9.3 | HTTPS/SSL valid | Check `avae-backend.duckdns.org` cert | Valid, not expiring soon | ☐ | | |
| 9.4 | EC2 disk space monitored | Check disk usage after several uploads | Doesn't silently fill up again (recall the 8GB→20GB issue) | ☐ | 🟠 | |
| 9.5 | Container restart recovers cleanly | Restart Docker container | FastAPI + worker both come back up | ☐ | | |
| 9.6 | S3 upload/download reliability | Upload doc, then view/download it later | File retrievable without error | ☐ | | |
| 9.7 | Concurrent users (simulate 2-3 tabs) | Use app from multiple sessions at once | No data collision/race conditions | ☐ | | |

---

## Bug Log (fill as you find issues)

| ID | Feature Area | Severity | Description | Steps to Reproduce | Status |
|---|---|---|---|---|---|
| BUG-001 | | | | | Open |

---

## Priority Fix Order (fill after full test pass)
1. 🔴 Critical bugs first
2. 🟠 High severity next
3. 🟡 Medium — batch these together
4. ⚪ Low — defer or list as "known issues"
