#!/usr/bin/env python3
"""
Re-queue a document for processing by sending its SQS message again.

Use when a document is stuck in PENDING (SQS message was lost or deleted).

Usage:
  python scripts/requeue_task.py 25
  python scripts/requeue_task.py 25 --dry-run
"""
import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Re-queue a document for processing")
    parser.add_argument("task_id", help="Document/task ID to re-queue (e.g. 25)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be sent, don't send")
    args = parser.parse_args()

    task_id = args.task_id.strip()
    try:
        doc_id = int(task_id)
    except ValueError:
        print("Error: task_id must be numeric", file=sys.stderr)
        sys.exit(1)

    from app.database import SessionLocal
    from app.db_models import Document
    from app.aws_services import aws_services
    from app.dependencies import redis_client
    from app.config import settings
    from app.api_registry import validate_audit_target

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            print(f"Error: Document {task_id} not found", file=sys.stderr)
            sys.exit(1)

        audit_target = doc.audit_target or "epc"
        try:
            audit_target = validate_audit_target(audit_target)
        except ValueError:
            audit_target = "epc"

        sqs_message = {
            "task_id": task_id,
            "s3_bucket": settings.s3_bucket_name,
            "s3_key": doc.s3_key,
            "filename": doc.filename,
            "created_at": datetime.now().isoformat(),
            "prompt": doc.prompt or "",
            "audit_target": audit_target,
        }

        if args.dry_run:
            print(f"Would re-queue task {task_id}:")
            print(f"  filename: {doc.filename}")
            print(f"  s3_key: {doc.s3_key}")
            print(f"  audit_target: {audit_target}")
            print("\nRun without --dry-run to actually send.")
            return 0

        # Update Redis
        task_data = {
            "task_id": task_id,
            "document_id": doc_id,
            "status": "PENDING",
            "progress": 0,
            "filename": doc.filename,
            "s3_key": doc.s3_key,
            "s3_bucket": settings.s3_bucket_name,
            "created_at": doc.created_at.isoformat() if doc.created_at else datetime.now().isoformat(),
            "started_at": "",
            "completed_at": "",
            "error": "",
            "prompt": doc.prompt or "",
            "audit_target": audit_target,
        }
        redis_client.hset(f"task:{task_id}", mapping=task_data)

        # Send to SQS
        message_id = aws_services.send_message_to_sqs(
            message_body=sqs_message,
            message_attributes={"task_id": task_id},
        )
        if not message_id:
            print("Error: Failed to send message to SQS", file=sys.stderr)
            sys.exit(1)

        # Reset document status if it was FAILED
        if doc.status == "FAILED":
            doc.status = "PENDING"
            doc.error_message = None
            doc.started_at = None
            doc.completed_at = None
            db.commit()
            print(f"Reset document {task_id} status to PENDING")

        print(f"Re-queued task {task_id} (message_id={message_id})")
        print("Start the worker to process: python3 -m app.sqs_worker")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
