#!/usr/bin/env python3
"""
Send a test message to SQS to verify the worker receives it.
Run: python3 scripts/send_test_message.py

If the worker picks it up, the queue/worker connection is fine.
If not, the API and worker may be using different queues or credentials.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.aws_services import aws_services


def main():
    print("Sending test message to SQS...")
    print(f"Queue: {settings.effective_sqs_queue_url}")
    print()

    # Message with invalid task_id so worker rejects immediately (we just want to verify receive)
    msg = {
        "task_id": "test-msg",
        "s3_bucket": settings.s3_bucket_name,
        "s3_key": "uploads/test-message.pdf",
        "filename": "test-message.pdf",
        "created_at": "2025-01-01T00:00:00",
        "prompt": "",
        "audit_target": "epc",
    }

    try:
        msg_id = aws_services.send_message_to_sqs(msg, message_attributes={"task_id": "test-msg"})
        if msg_id:
            print(f"✅ Sent message: {msg_id}")
            print()
            print("Watch the worker terminal. You should see:")
            print("  📨 Received message for task: test-msg")
            print("  ❌ Invalid task_id 'test-msg' (must be numeric). Deleting poison message.")
            print()
            print("If the worker shows NOTHING, API and worker may use different queues.")
        else:
            print("❌ Failed to send message")
            return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
