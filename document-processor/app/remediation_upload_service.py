"""
Remediation upload service (Task 5.6).

Process upload of replacement document for AWAITING_CLIENT_REMEDIATION checkpoint.
"""
import uuid

from app.aws_services import aws_services
from app.config import settings
from app.database import SessionLocal
from app.db_models import Document
from app.dependencies import redis_client


def validate_remediation_upload(checkpoint_id: str, user_id: int) -> Document:
    """
    Validate that checkpoint can receive a remediation upload.

    Raises:
        ValueError: If not found, wrong status, or wrong user
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == int(checkpoint_id)).first()
        if not doc:
            raise ValueError(f"Document not found: {checkpoint_id}")
        if doc.status != "AWAITING_CLIENT_REMEDIATION":
            raise ValueError(
                f"Document must be in AWAITING_CLIENT_REMEDIATION to accept remediation upload; current status: {doc.status}"
            )
        if doc.user_id != user_id:
            raise ValueError("Document does not belong to this user")
        return doc
    finally:
        db.close()


def process_remediation_upload(
    checkpoint_id: str,
    user_id: int,
    file_content: bytes,
    filename: str,
) -> str:
    """
    Process remediation upload: update Document, Redis, send SQS (Task 5.6).

    Returns:
        task_id (checkpoint_id) for the queued task
    """
    doc = validate_remediation_upload(checkpoint_id, user_id)
    task_id = str(doc.id)
    audit_target = doc.audit_target or "epc"

    file_extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".pdf"
    s3_key = f"uploads/{task_id}_remediation_{uuid.uuid4().hex[:12]}{file_extension}"

    # Upload to S3
    upload_success = aws_services.upload_file_to_s3(
        file_content=file_content,
        s3_key=s3_key,
        content_type="application/pdf",
    )
    if not upload_success:
        raise RuntimeError(f"Failed to upload {filename} to S3")

    # Update Document
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == int(task_id)).first()
        if document:
            document.s3_key = s3_key
            document.filename = filename
            document.status = "PENDING"
            document.completed_at = None
            document.result_text = None
            document.started_at = None
            db.commit()
    finally:
        db.close()

    # Update Redis
    task_data = {
        "task_id": task_id,
        "document_id": int(task_id),
        "status": "PENDING",
        "progress": 0,
        "filename": filename,
        "s3_key": s3_key,
        "s3_bucket": settings.s3_bucket_name,
        "created_at": doc.created_at.isoformat() if doc.created_at else "",
        "started_at": "",
        "completed_at": "",
        "error": "",
        "prompt": doc.prompt or "",
        "audit_target": audit_target,
    }
    redis_client.hset(f"task:{task_id}", mapping=task_data)

    # Send SQS message
    from datetime import datetime

    sqs_message = {
        "task_id": task_id,
        "s3_bucket": settings.s3_bucket_name,
        "s3_key": s3_key,
        "filename": filename,
        "created_at": datetime.now().isoformat(),
        "prompt": doc.prompt or "",
        "audit_target": audit_target,
    }
    message_id = aws_services.send_message_to_sqs(
        message_body=sqs_message,
        message_attributes={"task_id": task_id},
    )
    if not message_id:
        raise RuntimeError("Failed to queue remediation task to SQS")

    return task_id
