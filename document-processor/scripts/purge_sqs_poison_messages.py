#!/usr/bin/env python3
"""
Purge poison messages from SQS queue.

Poison messages (e.g. task_id=test-999, s3_key=uploads/test-999.pdf) block the worker
because the file doesn't exist in S3. This script receives and deletes them.

Usage:
  python scripts/purge_sqs_poison_messages.py
  python scripts/purge_sqs_poison_messages.py --dry-run  # Show what would be deleted
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.aws_services import aws_services
from app.config import settings


def is_poison_message(body: dict) -> bool:
    """Check if message is likely poison (invalid task_id)."""
    task_id = body.get("task_id", "")
    try:
        int(task_id)
        return False
    except (ValueError, TypeError):
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't delete, just report")
    args = parser.parse_args()

    print(f"Queue: {settings.effective_sqs_queue_url}")
    print("Receiving messages (max 10)...")
    messages = aws_services.receive_messages_from_sqs(max_messages=10, wait_time_seconds=1)
    if not messages:
        print("No messages in queue.")
        return

    poison_count = 0
    for msg in messages:
        body = msg.get("body", {})
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {}
        task_id = body.get("task_id", "?")
        s3_key = body.get("s3_key", "?")
        if is_poison_message(body):
            poison_count += 1
            print(f"  Poison: task_id={task_id}, s3_key={s3_key}")
            if not args.dry_run:
                aws_services.delete_message_from_sqs(msg["receipt_handle"])
                print(f"    Deleted.")
        else:
            print(f"  Valid:  task_id={task_id}, s3_key={s3_key} (keeping)")

    if poison_count:
        print(f"\n{'Would delete' if args.dry_run else 'Deleted'} {poison_count} poison message(s).")
        if args.dry_run:
            print("Run without --dry-run to actually delete.")
    else:
        print("\nNo poison messages found.")


if __name__ == "__main__":
    main()
