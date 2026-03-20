"""
Remediation email service (Task 5.6).

Generate templated email drafts for Request Client Remediation.
"""
from typing import Any

from app.database import SessionLocal
from app.db_models import Document, AuditLog


def _format_discrepancy_summary(flags: list[dict[str, Any]] | None) -> str:
    """Format discrepancy_flags as bullet list."""
    if not flags:
        return "One or more fields in the document do not match our verification records."
    lines = []
    for f in flags:
        field = f.get("field", "unknown")
        ext = f.get("extracted", "")
        api = f.get("api", "")
        if ext or api:
            lines.append(f"• {field}: extracted '{ext}' does not match registry '{api}'")
        else:
            lines.append(f"• {field}: mismatch identified")
    return "\n".join(lines) if lines else "One or more fields require verification."


def _get_template(audit_target: str) -> tuple[str, str]:
    """Return (subject_template, body_template) for audit_target."""
    subject = "Action Required: Document Verification — {filename}"
    body = """Dear Client,

Our verification process has identified discrepancies in the document you provided: {filename}.

{discrepancy_summary}

{officer_message}

Please upload a corrected document that addresses the issues above. You may reply to this email with the updated file attached, or use the upload link provided by your compliance officer.

Thank you,
Compliance Team"""
    return subject, body


def generate_remediation_email(
    checkpoint_id: str,
    officer_message: str | None = None,
) -> dict[str, str]:
    """
    Generate templated email draft for Request Client Remediation (Task 5.6).

    Args:
        checkpoint_id: Document/checkpoint ID
        officer_message: Optional custom message from officer

    Returns:
        {"subject": str, "body": str}

    Raises:
        ValueError: If document not found
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == int(checkpoint_id)).first()
        if not doc:
            raise ValueError(f"Document not found: {checkpoint_id}")

        # Latest audit log
        audit = (
            db.query(AuditLog)
            .filter(AuditLog.document_id == doc.id)
            .order_by(AuditLog.id.desc())
            .first()
        )

        discrepancy_summary = _format_discrepancy_summary(
            audit.discrepancy_flags if audit else None
        )
        officer_msg = (officer_message or "").strip()
        if officer_msg:
            officer_msg = f"\n\nAdditional note from your compliance officer:\n{officer_msg}"

        audit_target = doc.audit_target or "epc"
        sub_tpl, body_tpl = _get_template(audit_target)

        subject = sub_tpl.format(filename=doc.filename)
        body = body_tpl.format(
            filename=doc.filename,
            discrepancy_summary=discrepancy_summary,
            officer_message=officer_msg,
            audit_target=audit_target,
        )

        return {"subject": subject, "body": body}
    finally:
        db.close()
