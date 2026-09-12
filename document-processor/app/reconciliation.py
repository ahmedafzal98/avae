"""Reconciliation job for Issue #10.

Documents can get stuck in PENDING forever if the worker/container restarts
between the DB write (Document created with status=PENDING) and the SQS send
in the /upload endpoint (app/main.py) — a classic dual-write problem: one side
of the write succeeded, the other didn't, and nothing was left to retry it.

This job runs on a schedule (see sqs_worker.worker_loop) independently of the
SQS polling loop. Each run:
  1. Finds PENDING documents stuck past STUCK_THRESHOLD_MINUTES with retries left.
  2. Atomically claims each one (compare-and-swap on status) so a real worker
     racing to pick up the same document can't be double-processed.
  3. Re-sends the SQS message so the worker picks it up again.
  4. Finds PENDING documents stuck past the threshold that have exhausted their
     retries, and marks them FAILED_PERMANENT instead of retrying forever.
"""
import logging

from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal
from app.aws_services import aws_services
from app.sqs_message import build_processing_message

logger = logging.getLogger(__name__)

STUCK_THRESHOLD_MINUTES = 10
MAX_RETRY_COUNT = 5
BATCH_LIMIT = 50


def run_reconciliation() -> None:
    """Entry point called by the scheduler. Owns its own DB session."""
    db = SessionLocal()
    try:
        _reconcile_retryable(db)
        _reconcile_exhausted(db)
    except Exception:
        logger.exception("❌ Reconciliation run failed")
    finally:
        db.close()


def _reconcile_retryable(db) -> None:
    """Re-queue PENDING documents that are stuck but still have retries left."""
    candidate_ids = db.execute(
        text(
            """
            SELECT id FROM documents
            WHERE status = 'PENDING'
              AND created_at < NOW() - INTERVAL '10 minutes'
              AND retry_count < :max_retry
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
            """
        ),
        {"max_retry": MAX_RETRY_COUNT, "limit": BATCH_LIMIT},
    ).scalars().all()
    db.commit()

    if not candidate_ids:
        logger.info("🔎 Reconciliation: no stuck retryable documents found")
        return

    logger.info(f"🔎 Reconciliation: found {len(candidate_ids)} stuck retryable document(s)")
    for document_id in candidate_ids:
        _claim_and_requeue(db, document_id)


def _reconcile_exhausted(db) -> None:
    """Mark PENDING documents that are stuck AND have exhausted their retries."""
    candidate_ids = db.execute(
        text(
            """
            SELECT id FROM documents
            WHERE status = 'PENDING'
              AND created_at < NOW() - INTERVAL '10 minutes'
              AND retry_count >= :max_retry
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
            """
        ),
        {"max_retry": MAX_RETRY_COUNT, "limit": BATCH_LIMIT},
    ).scalars().all()
    db.commit()

    if not candidate_ids:
        return

    logger.info(f"🔎 Reconciliation: found {len(candidate_ids)} stuck document(s) with retries exhausted")
    for document_id in candidate_ids:
        _claim_and_fail_permanently(db, document_id)


def _claim_and_requeue(db, document_id: int) -> None:
    """Atomically claim one candidate, then re-send its SQS message."""
    row = db.execute(
        text(
            """
            UPDATE documents
            SET status = 'PROCESSING', started_at = NOW(), retry_count = retry_count + 1
            WHERE id = :id AND status = 'PENDING'
            RETURNING id, s3_key, filename, prompt, audit_target, retry_count
            """
        ),
        {"id": document_id},
    ).fetchone()
    db.commit()

    if row is None:
        logger.info(f"⏭️  Reconciliation: document {document_id} already claimed elsewhere, skipping")
        return

    _, s3_key, filename, prompt, audit_target, retry_count = row

    message = build_processing_message(
        task_id=str(document_id),
        s3_bucket=settings.s3_bucket_name,
        s3_key=s3_key,
        filename=filename,
        prompt=prompt,
        audit_target=audit_target or "epc",
    )
    message_id = aws_services.send_message_to_sqs(
        message_body=message,
        message_attributes={"task_id": str(document_id)},
    )

    if message_id:
        logger.warning(
            f"♻️  Reconciliation: re-queued stuck document {document_id} "
            f"(attempt {retry_count}/{MAX_RETRY_COUNT}, message_id={message_id})"
        )
    else:
        # Send failed after we already flipped status to PROCESSING — revert to PENDING
        # (keeping the incremented retry_count) so it isn't orphaned and gets retried
        # on the next reconciliation cycle instead of getting stuck in PROCESSING forever.
        db.execute(
            text("UPDATE documents SET status = 'PENDING' WHERE id = :id"),
            {"id": document_id},
        )
        db.commit()
        logger.error(
            f"❌ Reconciliation: failed to re-queue document {document_id}; "
            "reverted to PENDING for retry next cycle"
        )


def _claim_and_fail_permanently(db, document_id: int) -> None:
    """Atomically claim one exhausted candidate and mark it permanently failed."""
    row = db.execute(
        text(
            """
            UPDATE documents
            SET status = 'FAILED_PERMANENT',
                completed_at = NOW(),
                error_message = 'Exceeded maximum reconciliation retries'
            WHERE id = :id AND status = 'PENDING'
            RETURNING id, retry_count
            """
        ),
        {"id": document_id},
    ).fetchone()
    db.commit()

    if row is None:
        logger.info(f"⏭️  Reconciliation: document {document_id} already claimed elsewhere, skipping")
        return

    logger.error(
        f"❌ Reconciliation: document {document_id} exceeded {MAX_RETRY_COUNT} retries "
        f"(retry_count={row[1]}) — marked FAILED_PERMANENT"
    )
