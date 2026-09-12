"""Shared SQS message construction for document-processing tasks.

Used both when a document is first uploaded (app/main.py) and when the
reconciliation job re-queues a document stuck in PENDING (app/reconciliation.py),
so the two paths can't drift out of sync on message shape.
"""
from datetime import datetime
from typing import Any, Dict, Optional


def build_processing_message(
    task_id: str,
    s3_bucket: str,
    s3_key: str,
    filename: str,
    prompt: Optional[str],
    audit_target: str,
) -> Dict[str, Any]:
    """Build the SQS message body the worker expects for a document-processing task."""
    return {
        "task_id": task_id,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
        "filename": filename,
        "created_at": datetime.now().isoformat(),
        "prompt": prompt or "",
        "audit_target": audit_target,
    }
