#!/usr/bin/env python3
"""
Create a local SQS queue for development.
Use this when a deployed worker is consuming messages from the main queue,
preventing your local worker from receiving them.

Run: python3 scripts/create_local_queue.py

Then add to .env:
  SQS_QUEUE_URL_LOCAL=https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/pdf-processing-queue-local

Restart API and worker.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
import boto3
from botocore.exceptions import ClientError


def main():
    queue_name = "pdf-processing-queue-local"
    region = settings.aws_region

    sqs = boto3.client(
        "sqs",
        region_name=region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    try:
        # Get account ID from existing queue URL
        base_url = settings.sqs_queue_url
        # https://sqs.us-east-1.amazonaws.com/018139544641/pdf-processing-queue
        parts = base_url.rstrip("/").split("/")
        account_id = parts[-2] if len(parts) >= 2 else None
        if not account_id or not account_id.isdigit():
            print("Could not determine account ID from SQS_QUEUE_URL")
            return 1

        url = f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"

        try:
            sqs.get_queue_url(QueueName=queue_name)
            print(f"Queue already exists: {url}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "AWS.SimpleQueueService.NonExistentQueue":
                sqs.create_queue(QueueName=queue_name)
                print(f"Created queue: {url}")
            else:
                raise

        print()
        print("Add to your .env file:")
        print(f"  SQS_QUEUE_URL_LOCAL={url}")
        print()
        print("Then restart the API and worker.")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
