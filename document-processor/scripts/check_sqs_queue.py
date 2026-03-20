#!/usr/bin/env python3
"""
Check SQS queue depth and message counts.
Run from document-processor directory: python3 scripts/check_sqs_queue.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.aws_services import aws_services


def main():
    print("SQS Queue Check")
    print("=" * 50)
    print(f"Queue URL: {settings.effective_sqs_queue_url}")
    print(f"Region: {settings.aws_region}")
    print()

    try:
        attrs = aws_services.get_queue_attributes()
        if not attrs:
            print("Could not fetch queue attributes")
            return 1

        visible = int(attrs.get("ApproximateNumberOfMessages", 0))
        in_flight = int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0))
        delayed = int(attrs.get("ApproximateNumberOfMessagesDelayed", 0))

        print(f"Messages waiting:     {visible}")
        print(f"Messages in-flight:   {in_flight} (being processed)")
        print(f"Messages delayed:     {delayed}")
        print()

        if visible > 0:
            print("There are messages in the queue. Start the worker to process them:")
            print("  python3 -m app.sqs_worker")
        elif in_flight > 0:
            print("Messages are currently being processed by a worker.")
        else:
            print("Queue is empty. Upload a file to add messages.")

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
