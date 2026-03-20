"""
AVAE LangGraph nodes (Task 3.1).

Each node receives state, performs work, returns partial state update.
"""
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from app.aws_services import aws_services
from app.config import settings
from app.dependencies import redis_client
from app.database import SessionLocal
from app.db_models import Document, AuditLog
from app.extraction_service import extract_structured
from app.clients import fetch_company, fetch_land_data
from app.verification import verify_extraction
from app.tasks import (
    extract_text_from_pdf_legacy,
    extract_text_from_pdf,
    extract_metadata_from_pdf,
)
from app.schemas_api import PDFExtractionResult, PDFMetadata

from app.graph.state import AVAEState

logger = logging.getLogger(__name__)

VERIFIED = "VERIFIED"
DISCREPANCY_FLAG = "DISCREPANCY_FLAG"
EXTRACTED = "EXTRACTED"  # Extraction succeeded, no verification source (e.g. non-US financial)


def _update_progress(task_id: str, progress: int, status: str = "PROCESSING"):
    """Update task progress in Redis and PostgreSQL."""
    try:
        redis_client.hset(f"task:{task_id}", "progress", progress)
        redis_client.hset(f"task:{task_id}", "status", status)
        logger.info(f"📊 Task {task_id}: {progress}% complete")
        if status == "PROCESSING" and progress == 0:
            db = SessionLocal()
            try:
                document = db.query(Document).filter(Document.id == int(task_id)).first()
                if document and document.status != "PROCESSING":
                    document.status = "PROCESSING"
                    document.started_at = datetime.now()
                    db.commit()
            except Exception as db_error:
                logger.error(f"❌ Failed to update PostgreSQL status: {db_error}")
                db.rollback()
            finally:
                db.close()
    except Exception as e:
        logger.error(f"Error updating progress for {task_id}: {e}")


def burst_pdf(state: AVAEState) -> dict[str, Any]:
    """Download PDF from S3, burst into pages in memory (Task 4.1: PyMuPDF)."""
    task_id = state["task_id"]
    s3_key = state["s3_key"]
    filename = state["filename"]

    _update_progress(task_id, 0, "PROCESSING")
    logger.info(f"📥 Downloading from S3: {s3_key}")

    pdf_content = aws_services.download_file_from_s3(s3_key)
    if not pdf_content:
        return {"error": f"Failed to download file from S3: {s3_key}"}

    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp_file.write(pdf_content)
    temp_file_path = temp_file.name
    temp_file.close()
    logger.info(f"💾 Saved to temp file: {temp_file_path}")

    # Task 4.1: PyMuPDF burst into pages in memory
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_content, filetype="pdf")
        pages: list[dict[str, Any]] = []
        for i in range(len(doc)):
            page = doc[i]
            text = page.get_text() or ""
            pix = page.get_pixmap(dpi=150)
            image_bytes = pix.tobytes("png")
            pages.append({
                "page_num": i + 1,
                "text": text,
                "image_bytes": image_bytes,
                "width": pix.width,
                "height": pix.height,
            })
        doc.close()

        if not pages:
            return {"error": "PDF has no pages"}

        logger.info(f"📄 Burst into {len(pages)} page(s)")
    except Exception as e:
        logger.error(f"❌ PyMuPDF burst failed: {e}")
        return {"error": f"Failed to burst PDF: {e}"}

    return {
        "pdf_content": pdf_content,
        "temp_file_path": temp_file_path,
        "pages": pages,
    }


# Task 4.2: Page classification thresholds
_PAGE_TYPE_TEXT = "text"
_PAGE_TYPE_IMAGE = "image"
_PAGE_TYPE_TABLE = "table"
_PAGE_TYPE_CHART = "chart"
_IMAGE_TEXT_THRESHOLD = 50  # chars: below = image (scanned)
_TABLE_NEWLINE_RATIO = 0.04  # newlines/char: above = table-like
_CHART_TEXT_MAX = 200  # chars: 50-200 + large image = chart
_CHART_IMAGE_MIN_KB = 40  # min image size for chart (labels + visual)


def _classify_page(page: dict[str, Any]) -> str:
    """Heuristic page classifier: text vs image vs table vs chart."""
    text = (page.get("text") or "").strip()
    image_bytes = page.get("image_bytes") or b""
    text_len = len(text)
    image_kb = len(image_bytes) / 1024

    # Image: very little text (scanned/image-only)
    if text_len < _IMAGE_TEXT_THRESHOLD:
        return _PAGE_TYPE_IMAGE

    # Table: high newline density (structured rows)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    line_count = len(lines)
    newline_count = text.count("\n")
    newline_ratio = newline_count / max(1, text_len)
    if newline_ratio >= _TABLE_NEWLINE_RATIO and line_count >= 4:
        return _PAGE_TYPE_TABLE

    # Chart: moderate text (labels) + large image (visual)
    if _IMAGE_TEXT_THRESHOLD <= text_len <= _CHART_TEXT_MAX and image_kb >= _CHART_IMAGE_MIN_KB:
        return _PAGE_TYPE_CHART

    return _PAGE_TYPE_TEXT


def classify_pages(state: AVAEState) -> dict[str, Any]:
    """Classify pages by type: text, image, table, chart (Task 4.2)."""
    pages = state.get("pages", [])
    page_classifications = []
    for i, p in enumerate(pages):
        page_num = p.get("page_num", i + 1)
        page_type = _classify_page(p)
        page_classifications.append({"page_num": page_num, "type": page_type})
    type_counts = {}
    for pc in page_classifications:
        t = pc["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    logger.info(f"📋 Classified {len(pages)} page(s): {type_counts}")
    return {"page_classifications": page_classifications}


def _extract_single_page(
    page: dict[str, Any],
    page_num: int,
    page_type: str,
) -> tuple[int, str]:
    """
    Extract text from a single page. Used by extract_parallel (Task 4.5).
    Returns (page_num, text) for ordering. Imports inside to avoid circular deps.
    """
    try:
        if page_type == _PAGE_TYPE_IMAGE:
            from app.extractors.textract_extractor import extract_text_from_image

            image_bytes = page.get("image_bytes") or b""
            text = extract_text_from_image(image_bytes) or ""
            if text:
                logger.info(f"   Page {page_num}: Textract OCR ({len(text)} chars)")
            else:
                logger.warning(f"   Page {page_num}: Textract returned empty")
        elif page_type == _PAGE_TYPE_CHART:
            from app.extractors.vlm_extractor import extract_chart_summary

            image_bytes = page.get("image_bytes") or b""
            text = extract_chart_summary(image_bytes) or ""
            if text:
                logger.info(f"   Page {page_num}: VLM chart summary ({len(text)} chars)")
            else:
                logger.warning(f"   Page {page_num}: VLM returned empty, falling back to PyMuPDF")
                text = (page.get("text") or "").strip()
        else:
            text = (page.get("text") or "").strip()
        return (page_num, text or "")
    except Exception as e:
        logger.warning(f"   Page {page_num}: extraction failed: {e}")
        return (page_num, (page.get("text") or "").strip())


def extract_parallel(state: AVAEState) -> dict[str, Any]:
    """Extract text per page in parallel: Textract for image, VLM for chart, PyMuPDF for others (Task 4.3–4.5)."""
    task_id = state["task_id"]
    filename = state["filename"]
    pages = state.get("pages", [])
    page_classifications = state.get("page_classifications", [])

    _update_progress(task_id, 20, "PROCESSING")
    logger.info(f"📄 Extracting text from {filename}...")

    # Build page_num -> type map
    type_by_page: dict[int, str] = {
        pc.get("page_num", i + 1): pc.get("type", "text")
        for i, pc in enumerate(page_classifications)
    }

    max_workers = getattr(settings, "extraction_max_workers", 6)
    results: list[tuple[int, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _extract_single_page,
                page,
                page.get("page_num", i + 1),
                type_by_page.get(page.get("page_num", i + 1), "text"),
            ): page.get("page_num", i + 1)
            for i, page in enumerate(pages)
        }
        for future in as_completed(futures):
            try:
                page_num, text = future.result()
                results.append((page_num, text))
            except Exception as e:
                logger.warning(f"   Page {futures.get(future, '?')}: future failed: {e}")

    # Sort by page_num to preserve order
    results.sort(key=lambda x: x[0])

    # Build page_extractions for merge step (Task 4.6)
    type_by_num = type_by_page
    page_extractions: list[dict[str, Any]] = []
    fallback_extracted_text: str | None = None
    fallback_page_count: int | None = None

    if results and any(t for _, t in results):
        # Per-page extraction succeeded
        for page_num, text in results:
            if text:
                page_extractions.append({
                    "page_num": page_num,
                    "type": type_by_num.get(page_num, "text"),
                    "content": text,
                })
    elif state.get("temp_file_path"):
        # Fallback: legacy + LlamaParse on whole doc
        temp_file_path = state["temp_file_path"]
        logger.warning("⚠️  No per-page extraction; falling back to legacy + LlamaParse")
        text, page_count = extract_text_from_pdf_legacy(temp_file_path)
        if not text or len(text.strip()) < 50:
            text, page_count = extract_text_from_pdf(temp_file_path)
        fallback_extracted_text = text or ""
        fallback_page_count = page_count or len(pages) or 1

    _update_progress(task_id, 40, "PROCESSING")

    out: dict[str, Any] = {"page_extractions": page_extractions}
    if fallback_extracted_text is not None:
        out["extracted_text"] = fallback_extracted_text
        out["page_count"] = fallback_page_count or 1
    return out


def merge_extractions(state: AVAEState) -> dict[str, Any]:
    """
    Merge step (Task 4.6): combine Markdown + Textract + VLM summaries before normalize.

    Takes page_extractions (from extract_parallel) and produces a single extracted_text string.
    If fallback was used, extracted_text is already set — pass through.
    """
    page_extractions = state.get("page_extractions") or []
    extracted_text = state.get("extracted_text")
    pages = state.get("pages") or []

    if extracted_text is not None:
        # Fallback path: extract_parallel already set extracted_text
        return {"extracted_text": extracted_text, "page_count": state.get("page_count") or len(pages) or 1}

    if not page_extractions:
        return {"extracted_text": "", "page_count": len(pages) or 1}

    # Merge per-page content: preserve page order, add page headers
    parts = [f"--- Page {pe['page_num']} ---\n{pe['content']}" for pe in page_extractions if pe.get("content")]
    extracted_text = "\n\n".join(parts) if parts else ""
    page_count = len(pages) or len(page_extractions) or 1

    logger.debug(f"Merge: combined {len(page_extractions)} page(s) into {len(extracted_text)} chars")
    return {"extracted_text": extracted_text, "page_count": page_count}


def normalize(state: AVAEState) -> dict[str, Any]:
    """Structured LLM extraction."""
    extracted_text = state["extracted_text"]
    audit_target = state["audit_target"]

    extracted_json = extract_structured(extracted_text, audit_target)
    return {"extracted_json": extracted_json}


def fetch_api(state: AVAEState) -> dict[str, Any]:
    """Fetch ground truth from external API."""
    audit_target = state["audit_target"]
    extracted_json = state.get("extracted_json")

    api_response = None
    if extracted_json:
        try:
            if audit_target == "companies_house":
                cn = extracted_json.get("company_number", "")
                api_response = fetch_company(cn)
            elif audit_target == "hm_land_registry":
                addr = extracted_json.get("property_address", "")
                api_response = fetch_land_data(addr)
            elif audit_target == "epc":
                api_response = None
        except Exception as api_err:
            logger.warning(f"⚠️  API fetch failed: {api_err}")
            api_response = None

    return {"api_response": api_response}


def verify(state: AVAEState) -> dict[str, Any]:
    """Compare extracted vs API response."""
    audit_target = state["audit_target"]
    extracted_json = state.get("extracted_json")
    api_response = state.get("api_response")

    result = verify_extraction(audit_target, extracted_json or {}, api_response)
    return {
        "verification_status": result.status,
        "discrepancy_flags": result.discrepancy_flags,
        "fields_compared": result.fields_compared,
    }


def route_hitl(state: AVAEState) -> str:
    """Route based on verification status. Returns next node name."""
    status = state.get("verification_status", "")
    if status in (VERIFIED, EXTRACTED):
        return "persist"
    return "human_review"


def human_review(state: AVAEState, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    HITL node (Task 5.1): Build checkpoint_id and document_preview for human review.

    LangGraph passes config with configurable.thread_id. Pause/resume uses thread_id.
    """
    task_id = state.get("task_id", "")
    flags = state.get("discrepancy_flags", [])

    # checkpoint_id = thread_id for resume (Task 5.3)
    checkpoint_id = ""
    if config and isinstance(config.get("configurable"), dict):
        checkpoint_id = config["configurable"].get("thread_id", task_id)
    checkpoint_id = checkpoint_id or task_id

    logger.info(
        f"📋 Human review required for task {task_id} (DISCREPANCY_FLAG, {len(flags)} flag(s))"
    )
    for f in flags[:5]:
        logger.info(f"   — {f.get('field', '?')}: extracted={f.get('extracted')!r} vs api={f.get('api')!r}")
    if len(flags) > 5:
        logger.info(f"   ... and {len(flags) - 5} more")

    # Build document_preview (Task 5.1)
    extracted_text = state.get("extracted_text", "") or ""
    preview_len = 500
    extracted_text_preview = extracted_text[:preview_len] + ("..." if len(extracted_text) > preview_len else "")

    from app.schemas_hitl import DocumentPreview

    document_preview = DocumentPreview(
        task_id=task_id,
        filename=state.get("filename", ""),
        audit_target=state.get("audit_target", ""),
        verification_status=state.get("verification_status", "DISCREPANCY_FLAG"),
        page_count=state.get("page_count", 0),
        extracted_json=state.get("extracted_json") or {},
        api_response=state.get("api_response"),
        extracted_text_preview=extracted_text_preview,
        discrepancy_count=len(flags),
    ).model_dump()

    return {
        "hitl_checkpoint_id": checkpoint_id,
        "document_preview": document_preview,
    }


def handle_error(state: AVAEState) -> dict[str, Any]:
    """Handle pipeline error: update status to FAILED."""
    task_id = state["task_id"]
    filename = state["filename"]
    error_msg = state.get("error", "Unknown error")

    logger.error(f"❌ Error processing {filename}: {error_msg}")

    redis_client.hset(f"task:{task_id}", "status", "FAILED")
    redis_client.hset(f"task:{task_id}", "error", error_msg)
    redis_client.hset(f"task:{task_id}", "completed_at", datetime.now().isoformat())

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == int(task_id)).first()
        if document:
            document.status = "FAILED"
            document.error_message = error_msg
            document.completed_at = datetime.now()
            db.commit()
    except Exception as db_err:
        logger.error(f"❌ Failed to save error to PostgreSQL: {db_err}")
        db.rollback()
    finally:
        db.close()

    return {}


def persist(state: AVAEState) -> dict[str, Any]:
    """Save to audit_logs, Document, Redis."""
    task_id = state["task_id"]
    filename = state["filename"]
    audit_target = state.get("audit_target", "epc")
    # Prefer Document.audit_target (source of truth from upload) if worker passed wrong value
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == int(task_id)).first()
        if doc and doc.audit_target:
            audit_target = doc.audit_target
    finally:
        db.close()
    extracted_json = state.get("extracted_json")
    api_response = state.get("api_response")
    verification_status = state.get("verification_status", "PENDING")
    discrepancy_flags = state.get("discrepancy_flags", [])
    fields_compared = state.get("fields_compared", [])
    extracted_text = state.get("extracted_text", "")
    page_count = state.get("page_count", 0)
    temp_file_path = state.get("temp_file_path")
    prompt = state.get("prompt", "")

    start_time = datetime.now()
    _update_progress(task_id, 70, "PROCESSING")

    # Metadata
    metadata = {}
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            meta = extract_metadata_from_pdf(temp_file_path)
            metadata = meta.model_dump() if meta else {}
        except Exception:
            pass

    # Audit log
    db = SessionLocal()
    try:
        if extracted_json is not None:
            audit_log = AuditLog(
                document_id=int(task_id),
                audit_target=audit_target,
                extracted_json=extracted_json,
                api_response_json=api_response,
                verification_status=verification_status,
                discrepancy_flags=discrepancy_flags,
                fields_compared=fields_compared,
            )
            db.add(audit_log)
        db.commit()
    except Exception as db_err:
        logger.error(f"❌ Failed to save audit_log: {db_err}")
        db.rollback()
    finally:
        db.close()

    end_time = datetime.now()
    extraction_time = (end_time - start_time).total_seconds()

    # Result
    result = PDFExtractionResult(
        task_id=task_id,
        filename=filename,
        page_count=page_count,
        text=extracted_text,
        metadata=PDFMetadata(**metadata) if metadata else PDFMetadata(),
        extraction_time_seconds=round(extraction_time, 2),
        summary=None,
    )

    # Task 3.4: VERIFIED/EXTRACTED → COMPLETED; DISCREPANCY_FLAG → PENDING_HUMAN_REVIEW
    doc_status = "COMPLETED" if verification_status in (VERIFIED, EXTRACTED) else "PENDING_HUMAN_REVIEW"

    # Redis
    redis_client.setex(
        f"result:{task_id}",
        settings.task_result_ttl,
        result.model_dump_json(),
    )
    redis_client.hset(f"task:{task_id}", "status", doc_status)
    redis_client.hset(f"task:{task_id}", "completed_at", end_time.isoformat())
    redis_client.hset(f"task:{task_id}", "progress", 100)

    _update_progress(task_id, 100, doc_status)

    # PostgreSQL Document
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == int(task_id)).first()
        if document:
            document.status = doc_status
            document.result_text = extracted_text
            document.page_count = page_count
            document.extraction_time_seconds = extraction_time
            document.completed_at = end_time
            document.prompt = prompt or None
            db.commit()
            logger.info(f"💾 Saved result to PostgreSQL (document_id={task_id})")
    except Exception as db_err:
        logger.error(f"❌ Failed to save to PostgreSQL: {db_err}")
        db.rollback()
    finally:
        db.close()

    # Cleanup temp file
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
            logger.info(f"🗑️  Cleaned up temp file: {temp_file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")

    logger.info(
        f"✅ Persisted {filename} in {extraction_time:.2f}s (status={doc_status})"
    )
    logger.info(f"   📊 Stats: {page_count} pages, {len(extracted_text)} chars")

    return {"metadata": metadata}
