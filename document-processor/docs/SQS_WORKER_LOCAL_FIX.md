# SQS Worker Not Receiving Messages — Fix Guide

## Root Cause

When `ApproximateNumberOfMessagesNotVisible` is > 0 but your local worker shows "No messages in queue", **another consumer** is receiving the messages. Common causes:

1. **Deployed worker** (Fly.io, AWS, etc.) polling the same queue
2. **Another local worker** running in a different terminal
3. **Messages stuck in visibility timeout** from a crashed worker (wait 15 min for them to reappear)

## Solution: Use a Local-Only Queue

Create a separate SQS queue for local development so deployed workers don't steal your messages.

### Step 1: Create the queue in AWS

**Option A — AWS Console**
1. Go to [SQS Console](https://console.aws.amazon.com/sqs/)
2. Create queue → Name: `pdf-processing-queue-local` → Standard queue
3. Copy the queue URL

**Option B — AWS CLI** (if you have `sqs:CreateQueue` permission)
```bash
aws sqs create-queue --queue-name pdf-processing-queue-local --region us-east-1
```

### Step 2: Add to .env

```bash
# Add this line to document-processor/.env
SQS_QUEUE_URL_LOCAL=https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/pdf-processing-queue-local
```

Replace `YOUR_ACCOUNT_ID` with your AWS account ID (e.g. `018139544641` from your main queue URL).

### Step 3: Restart API and worker

```bash
# Stop both (Ctrl+C), then:
uvicorn app.main:app --reload --port 8000   # Terminal 1
python3 app/sqs_worker.py                   # Terminal 2
```

Both will now use the local queue. Upload from the frontend — the worker should receive messages.

## Verify

1. **Run test script:**
   ```bash
   python3 scripts/send_test_message.py
   ```
   Worker should log: `📨 Received message for task: test-msg`

2. **Upload from frontend** — worker should process it.

## If You Can't Create a New Queue

- **Stop any deployed workers** when testing locally
- **Check for multiple local workers:** ensure only one `python3 app/sqs_worker.py` is running
- **Wait 15 minutes** if messages are stuck in visibility timeout from a crashed worker
