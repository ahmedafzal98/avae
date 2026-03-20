"""
Audit log listing for Phase 7 (Audit Log UI).

List audit_logs with document info; supports filters and pagination.
"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_

from app.database import SessionLocal
from app.db_models import AuditLog, Document


def _parse_date(s: str) -> datetime | None:
    """Parse YYYY-MM-DD to datetime at start of day (UTC)."""
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    except ValueError:
        return None


def list_audit_logs(
    status: str | None = None,
    audit_target: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """
    List audit log entries (latest per document or all — currently all rows).

    Each row is one AuditLog joined with Document for filename.
    date_from / date_to: optional YYYY-MM-DD; filter by AuditLog.created_at (inclusive range).
    search: optional; matches filename (case-insensitive) or document_id (exact/prefix).
    """
    db = SessionLocal()
    try:
        query = (
            db.query(AuditLog, Document)
            .join(Document, AuditLog.document_id == Document.id)
            .order_by(AuditLog.created_at.desc())
        )
        if status:
            query = query.filter(AuditLog.verification_status == status)
        if audit_target:
            query = query.filter(AuditLog.audit_target == audit_target)
        from_dt = _parse_date(date_from) if date_from else None
        to_dt = _parse_date(date_to) if date_to else None
        if from_dt is not None:
            query = query.filter(AuditLog.created_at >= from_dt)
        if to_dt is not None:
            # End of day (inclusive)
            end_of_day = to_dt + timedelta(days=1)
            query = query.filter(AuditLog.created_at < end_of_day)
        if search and search.strip():
            term = search.strip()
            filename_match = Document.filename.ilike(f"%{term}%")
            # Match document_id if term is numeric (exact or prefix)
            if term.isdigit():
                doc_id_match = AuditLog.document_id == int(term)
                query = query.filter(or_(filename_match, doc_id_match))
            else:
                query = query.filter(filename_match)

        total = query.count()
        offset = (page - 1) * page_size
        rows = query.offset(offset).limit(page_size).all()

        items = []
        for audit, doc in rows:
            items.append({
                "id": audit.id,
                "document_id": audit.document_id,
                "created_at": audit.created_at.isoformat() if audit.created_at else "",
                "audit_target": audit.audit_target or "epc",
                "verification_status": audit.verification_status or "PENDING",
                "filename": doc.filename if doc else "",
            })
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    finally:
        db.close()


def get_audit_health_stats(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """
    Aggregate stats for Audit Health Index (Phase 7.7).

    Returns total, verified, discrepancy_flag, pending_human_review, success_rate (0–100).
    Optional trend: compare current period to previous period of same length;
    returns trend_direction ("up" | "down" | "stable") and trend_value (percentage point change).
    """
    db = SessionLocal()
    try:
        from_dt = _parse_date(date_from) if date_from else None
        to_dt = _parse_date(date_to) if date_to else None

        base_query = db.query(AuditLog.verification_status, func.count(AuditLog.id)).group_by(
            AuditLog.verification_status
        )
        if from_dt is not None:
            base_query = base_query.filter(AuditLog.created_at >= from_dt)
        if to_dt is not None:
            end_of_day = to_dt + timedelta(days=1)
            base_query = base_query.filter(AuditLog.created_at < end_of_day)

        rows = base_query.all()
        total = sum(r[1] for r in rows)
        verified = next((r[1] for r in rows if r[0] == "VERIFIED"), 0)
        discrepancy_flag = next((r[1] for r in rows if r[0] == "DISCREPANCY_FLAG"), 0)
        pending = next((r[1] for r in rows if r[0] == "PENDING_HUMAN_REVIEW"), 0)
        success_rate = round(100.0 * verified / total, 1) if total else 0.0

        result: dict[str, Any] = {
            "total": total,
            "verified": verified,
            "discrepancy_flag": discrepancy_flag,
            "pending_human_review": pending,
            "success_rate": success_rate,
        }

        # Trend: compare to previous period of same length (e.g. last 30 days vs previous 30)
        if from_dt is not None and to_dt is not None and total > 0:
            period_days = (to_dt - from_dt).days + 1
            if period_days >= 1:
                prev_end = from_dt - timedelta(days=1)
                prev_start = prev_end - timedelta(days=period_days - 1)
                prev_query = (
                    db.query(AuditLog.verification_status, func.count(AuditLog.id))
                    .filter(AuditLog.created_at >= prev_start)
                    .filter(AuditLog.created_at < from_dt)
                    .group_by(AuditLog.verification_status)
                )
                prev_rows = prev_query.all()
                prev_total = sum(r[1] for r in prev_rows)
                prev_verified = next((r[1] for r in prev_rows if r[0] == "VERIFIED"), 0)
                prev_rate = round(100.0 * prev_verified / prev_total, 1) if prev_total else 0.0
                trend_pp = round(success_rate - prev_rate, 1)
                if trend_pp > 0:
                    result["trend_direction"] = "up"
                elif trend_pp < 0:
                    result["trend_direction"] = "down"
                else:
                    result["trend_direction"] = "stable"
                result["trend_value"] = abs(trend_pp)
        else:
            result["trend_direction"] = "stable"
            result["trend_value"] = 0.0

        return result
    finally:
        db.close()


def get_audit_log_detail(audit_log_id: int) -> dict[str, Any] | None:
    """
    Fetch a single audit log by id with full details (Phase 7.9 expand row).
    Returns None if not found.
    """
    db = SessionLocal()
    try:
        row = (
            db.query(AuditLog, Document)
            .join(Document, AuditLog.document_id == Document.id)
            .filter(AuditLog.id == audit_log_id)
            .first()
        )
        if not row:
            return None
        audit, doc = row
        return {
            "id": audit.id,
            "document_id": audit.document_id,
            "created_at": audit.created_at.isoformat() if audit.created_at else "",
            "audit_target": audit.audit_target or "epc",
            "verification_status": audit.verification_status or "PENDING",
            "filename": doc.filename if doc else "",
            "extracted_json": audit.extracted_json or {},
            "api_response_json": audit.api_response_json,
            "discrepancy_flags": audit.discrepancy_flags,
            "fields_compared": audit.fields_compared,
        }
    finally:
        db.close()
