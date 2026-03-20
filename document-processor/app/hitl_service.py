"""
HITL service (Task 5.2, 5.3, 5.4, 5.5).

Override, Manual Correction, Request Client Remediation.
Resume logic: load checkpoint, inject decision, continue graph to persist.
Checkpoint listing: list documents awaiting human review.
Checkpoint TTL: expire PENDING_HUMAN_REVIEW after N days.
"""
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, and_

from app.config import settings
from app.database import SessionLocal
from app.db_models import Document, AuditLog

logger = logging.getLogger(__name__)


def _ensure_valid_task_id(checkpoint_id: str) -> None:
    """Raise if checkpoint_id is not a valid numeric task ID."""
    if not checkpoint_id:
        raise ValueError("checkpoint_id is required")
    try:
        int(checkpoint_id)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid checkpoint_id: must be numeric (document ID)")


def _ensure_pending_human_review(checkpoint_id: str) -> None:
    """Raise if document is not in PENDING_HUMAN_REVIEW."""
    _ensure_valid_task_id(checkpoint_id)
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == int(checkpoint_id)).first()
        if not doc:
            raise ValueError(f"Document not found: {checkpoint_id}")
        if doc.status != "PENDING_HUMAN_REVIEW":
            raise ValueError(f"Document not in PENDING_HUMAN_REVIEW: {doc.status}")
    finally:
        db.close()


def apply_override(checkpoint_id: str, field: str | None = None) -> dict[str, Any]:
    """
    Override: accept extracted value(s) as-is. Officer takes responsibility.

    Updates state with verification_status=VERIFIED, resumes graph to persist.
    """
    _ensure_pending_human_review(checkpoint_id)
    graph = _get_graph()
    config = {"configurable": {"thread_id": checkpoint_id}}

    # Update state: treat as verified (override = accept)
    values: dict[str, Any] = {
        "verification_status": "VERIFIED",
        "hitl_action": "override",
        "override_field": field,
    }
    try:
        fork_config = graph.update_state(config, values)
        final_state = graph.invoke(None, fork_config)
        return {
            "success": True,
            "message": "Override applied; document persisted.",
            "task_id": checkpoint_id,
            "status": final_state.get("verification_status", "VERIFIED"),
        }
    except Exception as e:
        logger.error("HITL override failed: %s", e)
        raise


def apply_manual_correction(checkpoint_id: str, corrections: dict[str, Any]) -> dict[str, Any]:
    """
    Manual Correction: officer corrects values; system treats as verified and persists.

    Merges corrections into extracted_json, sets verification_status=VERIFIED, resumes.
    """
    _ensure_pending_human_review(checkpoint_id)
    graph = _get_graph()
    config = {"configurable": {"thread_id": checkpoint_id}}

    # Get current state to merge corrections
    state = graph.get_state(config)
    if not state or not state.values:
        raise ValueError(f"Checkpoint not found: {checkpoint_id}")

    extracted = dict(state.values.get("extracted_json") or {})
    extracted.update(corrections)

    values = {
        "extracted_json": extracted,
        "verification_status": "VERIFIED",
        "hitl_action": "manual_correction",
    }
    try:
        fork_config = graph.update_state(config, values)
        final_state = graph.invoke(None, fork_config)
        return {
            "success": True,
            "message": "Manual correction applied; document persisted.",
            "task_id": checkpoint_id,
            "status": final_state.get("verification_status", "VERIFIED"),
        }
    except Exception as e:
        logger.error("HITL manual correction failed: %s", e)
        raise


def apply_request_client_remediation(checkpoint_id: str, message: str | None = None) -> dict[str, Any]:
    """
    Request Client Remediation: mark document as needing client fix. Pause indefinitely.

    Updates Document.status to AWAITING_CLIENT_REMEDIATION. No resume.
    Includes templated email draft (Task 5.6).
    """
    _ensure_valid_task_id(checkpoint_id)
    task_id = checkpoint_id
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == int(task_id)).first()
        if not doc:
            raise ValueError(f"Document not found: {task_id}")
        if doc.status != "PENDING_HUMAN_REVIEW":
            raise ValueError(f"Document not in PENDING_HUMAN_REVIEW: {doc.status}")

        doc.status = "AWAITING_CLIENT_REMEDIATION"
        if message:
            doc.error_message = (doc.error_message or "") + f"\n[Remediation] {message}"
        db.commit()

        # Update Redis
        from app.dependencies import redis_client

        redis_client.hset(f"task:{task_id}", "status", "AWAITING_CLIENT_REMEDIATION")

        # Generate templated email draft (Task 5.6)
        from app.remediation_email_service import generate_remediation_email

        email_draft = generate_remediation_email(checkpoint_id, message)

        return {
            "success": True,
            "message": "Request Client Remediation applied. Document paused until new upload.",
            "task_id": task_id,
            "status": "AWAITING_CLIENT_REMEDIATION",
            "email_draft": email_draft,
        }
    except ValueError:
        raise
    except Exception as e:
        logger.error("HITL request client remediation failed: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


def _get_graph():
    """Get compiled AVAE graph with checkpointer."""
    from app.graph import get_avae_graph

    return get_avae_graph()


def get_checkpoint_state(checkpoint_id: str) -> dict[str, Any] | None:
    """Get current state for a checkpoint (for listing/validation)."""
    graph = _get_graph()
    config = {"configurable": {"thread_id": checkpoint_id}}
    try:
        state = graph.get_state(config)
        return state.values if state else None
    except Exception:
        return None


def list_hitl_checkpoints(
    status: str | None = None,
    audit_target: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """
    List documents awaiting human review (Task 5.4).

    Queries Document with status IN (PENDING_HUMAN_REVIEW, AWAITING_CLIENT_REMEDIATION),
    joins latest AuditLog, applies filters, paginates.
    """
    db = SessionLocal()
    try:
        hitl_statuses = ("PENDING_HUMAN_REVIEW", "AWAITING_CLIENT_REMEDIATION")

        # Subquery: latest audit_log id per document
        latest_audit_subq = (
            db.query(
                AuditLog.document_id,
                func.max(AuditLog.id).label("audit_log_id"),
            )
            .group_by(AuditLog.document_id)
            .subquery()
        )

        # Base query: Document join latest AuditLog
        query = (
            db.query(Document, AuditLog)
            .join(latest_audit_subq, Document.id == latest_audit_subq.c.document_id)
            .join(AuditLog, AuditLog.id == latest_audit_subq.c.audit_log_id)
            .filter(Document.status.in_(hitl_statuses))
        )

        if status:
            query = query.filter(Document.status == status)
        if audit_target:
            query = query.filter(Document.audit_target == audit_target)

        # Count total
        total = query.count()

        # Paginate
        offset = (page - 1) * page_size
        rows = query.order_by(Document.created_at.desc()).offset(offset).limit(page_size).all()

        checkpoints = []
        for doc, audit in rows:
            checkpoints.append(
                {
                    "checkpoint_id": str(doc.id),
                    "filename": doc.filename,
                    "audit_target": doc.audit_target or "epc",
                    "status": doc.status,
                    "document_preview": audit.extracted_json if audit.extracted_json else None,
                    "discrepancy_flags": audit.discrepancy_flags,
                    "created_at": doc.created_at.isoformat() if doc.created_at else "",
                }
            )

        return {
            "checkpoints": checkpoints,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    finally:
        db.close()


def get_hitl_checkpoints_summary() -> dict[str, Any]:
    """
    Lightweight counts for Pending Reconciliation card (Phase 7.8).

    Returns total documents in HITL (PENDING_HUMAN_REVIEW + AWAITING_CLIENT_REMEDIATION)
    and breakdown by status.
    """
    db = SessionLocal()
    try:
        hitl_statuses = ("PENDING_HUMAN_REVIEW", "AWAITING_CLIENT_REMEDIATION")
        total = (
            db.query(Document.id)
            .filter(Document.status.in_(hitl_statuses))
            .count()
        )
        pending_review = (
            db.query(Document.id)
            .filter(Document.status == "PENDING_HUMAN_REVIEW")
            .count()
        )
        awaiting_client = (
            db.query(Document.id)
            .filter(Document.status == "AWAITING_CLIENT_REMEDIATION")
            .count()
        )
        return {
            "total": total,
            "pending_review": pending_review,
            "awaiting_client": awaiting_client,
        }
    finally:
        db.close()


def expire_hitl_checkpoints() -> dict[str, Any]:
    """
    Expire PENDING_HUMAN_REVIEW checkpoints older than TTL days (Task 5.5).

    Uses completed_at (fallback: created_at). AWAITING_CLIENT_REMEDIATION excluded.
    """
    from app.dependencies import redis_client

    cutoff = datetime.utcnow() - timedelta(days=settings.hitl_checkpoint_ttl_days)
    db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(
                Document.status == "PENDING_HUMAN_REVIEW",
                or_(
                    Document.completed_at < cutoff,
                    and_(
                        Document.completed_at.is_(None),
                        Document.created_at < cutoff,
                    ),
                ),
            )
            .all()
        )
        expired_count = 0
        for doc in docs:
            doc.status = "EXPIRED"
            task_id = str(doc.id)
            redis_client.hset(f"task:{task_id}", "status", "EXPIRED")
            expired_count += 1
        db.commit()
        logger.info("Expired %d HITL checkpoints (Task 5.5)", expired_count)
        return {"expired_count": expired_count, "message": f"Expired {expired_count} checkpoints"}
    except Exception as e:
        logger.error("HITL checkpoint expiry failed: %s", e)
        db.rollback()
        raise
    finally:
        db.close()
