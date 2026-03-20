"""SQS Worker - Replaces Celery for AWS-native processing (Task 3.3: invokes LangGraph)"""
import os
import sys
import time
import signal
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.aws_services import aws_services
from app.api_registry import validate_audit_target, get_valid_audit_targets
from app.dependencies import redis_client
from app.database import SessionLocal
from app.db_models import Document
from app.graph import run_avae_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info(f"⚠️  Received signal {signum}. Shutting down gracefully...")
    shutdown_requested = True


def _is_valid_task_id(task_id: str) -> bool:
    """Task ID must be numeric (Document.id from PostgreSQL)."""
    if not task_id:
        return False
    try:
        int(task_id)
        return True
    except (ValueError, TypeError):
        return False


def update_task_progress(task_id: str, progress: int, status: str = "PROCESSING"):
    """Update task progress in Redis and PostgreSQL"""
    try:
        # Update Redis (real-time)
        redis_client.hset(f"task:{task_id}", "progress", progress)
        redis_client.hset(f"task:{task_id}", "status", status)
        logger.info(f"📊 Task {task_id}: {progress}% complete")
        
        # ⭐ Update PostgreSQL status if PROCESSING (only for valid numeric task_id)
        if status == "PROCESSING" and progress == 0 and _is_valid_task_id(task_id):
            db = SessionLocal()
            try:
                document = db.query(Document).filter(Document.id == int(task_id)).first()
                if document and document.status != "PROCESSING":
                    document.status = "PROCESSING"
                    document.started_at = datetime.now()
                    db.commit()
                    logger.info(f"💾 Updated PostgreSQL: document {task_id} started processing")
            except Exception as db_error:
                logger.error(f"❌ Failed to update PostgreSQL status: {db_error}")
                db.rollback()
            finally:
                db.close()
    except Exception as e:
        logger.error(f"Error updating progress for {task_id}: {e}")


def process_pdf_from_s3(
    task_id: str,
    s3_bucket: str,
    s3_key: str,
    filename: str,
    prompt: str = "",
    audit_target: str = "epc",
) -> bool:
    """
    Process PDF file from S3 via LangGraph pipeline (Task 3.3).

    Delegates to run_avae_graph: burst_pdf → extract → normalize → fetch_api
    → verify → route_hitl → [persist | human_review → persist].

    Args:
        task_id: Unique task identifier
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        filename: Original filename
        prompt: Optional prompt (passed to graph; summary generation deferred)
        audit_target: AVAE audit target (epc, companies_house, hm_land_registry)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        redis_client.hset(f"task:{task_id}", "status", "PROCESSING")
        redis_client.hset(f"task:{task_id}", "started_at", datetime.now().isoformat())
        update_task_progress(task_id, 0, "PROCESSING")

        logger.info(f"🚀 Starting LangGraph pipeline: {filename} (Task: {task_id})")

        final_state = run_avae_graph(
            task_id=task_id,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            filename=filename,
            audit_target=audit_target,
            prompt=prompt,
        )

        if final_state.get("error"):
            logger.warning(f"⚠️  Graph completed with error: {final_state.get('error')}")
            return False

        logger.info(f"✅ LangGraph pipeline completed for {filename}")
        return True

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error processing {filename}: {error_msg}")

        redis_client.hset(f"task:{task_id}", "status", "FAILED")
        redis_client.hset(f"task:{task_id}", "error", error_msg)
        redis_client.hset(f"task:{task_id}", "completed_at", datetime.now().isoformat())

        if not _is_valid_task_id(task_id):
            return False
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == int(task_id)).first()
            if document:
                document.status = "FAILED"
                document.error_message = error_msg
                document.completed_at = datetime.now()
                db.commit()
                logger.info(f"💾 Saved error to PostgreSQL (document_id={task_id})")
        except Exception as db_error:
            logger.error(f"❌ Failed to save error to PostgreSQL: {db_error}")
            db.rollback()
        finally:
            db.close()

        return False


def worker_loop():
    """
    Main worker loop - polls SQS and processes messages
    """
    logger.info("=" * 70)
    logger.info("🚀 SQS Worker Started")
    logger.info("=" * 70)
    logger.info(f"Region: {settings.aws_region}")
    logger.info(f"Queue: {settings.effective_sqs_queue_url}")
    logger.info(f"S3 Bucket: {settings.s3_bucket_name}")
    logger.info("=" * 70)
    logger.info("Waiting for messages... (Press Ctrl+C to stop)")
    logger.info("")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while not shutdown_requested:
        try:
            logger.info("Polling SQS for messages...")
            messages = aws_services.receive_messages_from_sqs(
                max_messages=1,
                wait_time_seconds=5,  # Shorter for faster feedback when debugging
                visibility_timeout=900  # 15 minutes
            )
            
            # Reset error counter on successful poll
            consecutive_errors = 0
            
            if not messages:
                logger.info("No messages in queue, polling again...")
                continue
            
            # Process each message
            for message in messages:
                if shutdown_requested:
                    logger.info("⚠️  Shutdown requested, stopping message processing...")
                    break
                
                try:
                    # Extract message data
                    body = message['body']
                    receipt_handle = message['receipt_handle']
                    receive_count = message.get('receive_count', 1)
                    
                    task_id = body.get('task_id')
                    s3_bucket = body.get('s3_bucket')
                    s3_key = body.get('s3_key')
                    filename = body.get('filename')
                    prompt = body.get('prompt', '')
                    audit_target_raw = body.get('audit_target', 'epc')
                    # Prefer Document.audit_target (source of truth from upload) when task_id is valid
                    audit_target = None
                    if _is_valid_task_id(task_id):
                        from app.database import SessionLocal
                        from app.db_models import Document
                        db = SessionLocal()
                        try:
                            doc = db.query(Document).filter(Document.id == int(task_id)).first()
                            if doc and doc.audit_target:
                                audit_target = doc.audit_target
                        finally:
                            db.close()
                    if audit_target is None:
                        try:
                            audit_target = validate_audit_target(audit_target_raw)
                        except ValueError:
                            audit_target = "epc"
                            logger.warning(
                                f"⚠️ Invalid audit_target '{audit_target_raw}' for task {task_id}; "
                                f"using default 'epc'. Allowed: {', '.join(get_valid_audit_targets())}"
                            )

                    logger.info(f"📨 Received message for task: {task_id} (audit_target={audit_target})")
                    if prompt:
                        logger.info(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
                    
                    # Validate message data
                    if not all([task_id, s3_bucket, s3_key, filename]):
                        logger.error(f"❌ Invalid message format: {body}")
                        aws_services.delete_message_from_sqs(receipt_handle)
                        continue

                    # Reject poison messages: task_id must be numeric (Document.id)
                    if not _is_valid_task_id(task_id):
                        logger.error(
                            f"❌ Invalid task_id '{task_id}' (must be numeric). Deleting poison message."
                        )
                        aws_services.delete_message_from_sqs(receipt_handle)
                        continue
                    
                    # Process the PDF
                    success = process_pdf_from_s3(
                        task_id, s3_bucket, s3_key, filename, prompt, audit_target
                    )
                    
                    if success:
                        # Delete message from SQS (acknowledge processing)
                        aws_services.delete_message_from_sqs(receipt_handle)
                        logger.info(f"✅ Message processed and deleted from SQS")
                        logger.info("Ready for next message. Polling SQS...")
                    else:
                        # Poison message handling: after 3+ failures, delete to unblock queue
                        if receive_count >= 3:
                            logger.error(
                                f"❌ Task {task_id} failed {receive_count} times. Deleting poison message to unblock queue."
                            )
                            aws_services.delete_message_from_sqs(receipt_handle)
                        else:
                            logger.warning(
                                f"⚠️  Processing failed (attempt {receive_count}/3), message will be retried"
                            )
                
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    # Don't delete message - let SQS retry
        
        except KeyboardInterrupt:
            logger.info("⚠️  Keyboard interrupt received...")
            break
        
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"❌ Worker error: {e}")
            logger.error(f"Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.error("❌ Too many consecutive errors. Exiting...")
                break
            
            # Back off before retrying
            time.sleep(5)
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("🛑 SQS Worker Stopped")
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        worker_loop()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
