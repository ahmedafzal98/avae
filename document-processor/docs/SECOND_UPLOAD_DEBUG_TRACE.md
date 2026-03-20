# Second Upload Not Processing — Debug Trace

This document traces the execution flow to diagnose why the **second document upload** is saved to S3 but the SQS worker does not process it.

---

## Execution Flow Summary

```
Upload 1:  curl → FastAPI → S3 ✓ → PostgreSQL ✓ → Redis ✓ → SQS ✓ → Worker polls ✓ → process_pdf_from_s3 ✓ → delete message ✓
Upload 2:  curl → FastAPI → S3 ✓ → PostgreSQL ✓ → Redis ✓ → SQS ? → Worker polls ? → ???
```

**Known:** Second upload reaches S3 successfully.  
**Unknown:** Did the API return 202? Did SQS receive the message? Is the worker still running and polling?

---

## 1. Upload Phase (main.py:246–361)

For each file:

| Step | Code | What Happens |
|------|------|--------------|
| 1 | `task_id = str(uuid.uuid4())` | Generate unique UUID for S3 key |
| 2 | `s3_key = f"uploads/{task_id}{file_extension}"` | S3 key is unique per upload |
| 3 | `upload_file_to_s3(...)` | Upload to S3 |
| 4 | Create `Document` in PostgreSQL | Get new `document.id` |
| 5 | `task_id = str(document.id)` | **Overwrite** task_id with document ID |
| 6 | Redis `hset` + `rpush` | Store task metadata |
| 7 | `send_message_to_sqs(sqs_message)` | Enqueue job |
| 8 | If `message_id` is None → raise 500 | API would fail, not return 202 |

**Important:** If the API returns `202 Accepted` with `task_ids`, the SQS send succeeded. The message is in the queue.

**SQS message body (unique per upload):**
```json
{
  "task_id": "2",           // document.id — different for each upload
  "s3_bucket": "...",
  "s3_key": "uploads/<uuid>.pdf",  // different UUID each time
  "filename": "1790388 EPC.pdf",
  "created_at": "...",
  "prompt": "",
  "audit_target": "epc"
}
```

---

## 2. Worker Phase (sqs_worker.py)

### Main loop (worker_loop)

```
while not shutdown_requested:
    messages = receive_messages_from_sqs(max_messages=1, wait_time_seconds=20)
    for message in messages:
        process_pdf_from_s3(...)
        if success: delete_message_from_sqs(receipt_handle)
    # Loop continues → poll again
```

- **Single-threaded:** Processes one message, then polls again.
- **Long polling:** Waits up to 20 seconds for a message.
- After first message: deletes it, then immediately polls for the next.

### When would the worker NOT process the second message?

| Cause | How to verify |
|-------|----------------|
| Worker exited/crashed after first message | Check if worker process is still running |
| Worker stuck in `run_avae_graph()` | First message completed; unlikely unless graph hangs on second run |
| SQS FIFO deduplication | Message bodies differ (task_id, s3_key, created_at); unlikely |
| Wrong SQS queue URL | API and worker must use same `SQS_QUEUE_URL` |
| Message never sent | API would return 500, not 202 |
| Worker polling wrong queue | Compare `SQS_QUEUE_URL` in API vs worker env |

---

## 3. Diagnostic Commands

Run these **after** the second upload to isolate the failure.

### A. Confirm API returned 202 for second upload

```bash
# Re-run upload with verbose output
curl -v -X POST "http://localhost:8000/upload?user_id=1&audit_target=epc" \
  -F "files=@/Users/mbp/Desktop/redis/1790388 EPC.pdf"
```

Look for: `HTTP/1.1 202 Accepted` and `task_ids` in the response body.

### B. Check SQS queue depth

```bash
cd /Users/mbp/Desktop/redis/document-processor
python3 scripts/check_sqs_queue.py
```

- **Messages waiting > 0:** Message is in queue; worker is not receiving or not running.
- **Messages in-flight > 0:** Worker has received it but hasn’t finished (or crashed mid-processing).
- **Both 0:** Message was processed or never sent.

### C. Check worker is running and polling

Worker logs should show:

```
Polling SQS for messages...
```

If you see this repeatedly with no `📨 Received message for task:`, the queue is empty or the worker is polling a different queue.

### D. Verify queue URL consistency

```bash
# In the same shell where API and worker run
cd /Users/mbp/Desktop/redis/document-processor
grep SQS_QUEUE_URL .env
```

API and worker must use the same `SQS_QUEUE_URL`.

### E. Check for FIFO queue

```bash
# If queue URL ends with .fifo, it's a FIFO queue
echo $SQS_QUEUE_URL  # or check .env
```

FIFO queues use content-based deduplication when `MessageDeduplicationId` is not set. Message bodies differ per upload, so deduplication is unlikely, but worth confirming.

### F. Inspect documents in PostgreSQL

```bash
docker-compose exec postgres psql -U docuser -d document_processor -c \
  "SELECT id, filename, s3_key, status, created_at FROM documents ORDER BY id DESC LIMIT 5;"
```

- If the second document exists with `status = 'PENDING'`, the upload succeeded but the worker never processed it.
- If the second document has `status = 'PROCESSING'` or `'COMPLETED'`, the worker did process it.

### G. Inspect Redis task keys

```bash
redis-cli LRANGE all_tasks 0 -1
redis-cli HGETALL task:1
redis-cli HGETALL task:2
```

Confirm both tasks exist and their `status` values.

---

## 4. Most Likely Causes (Prioritized)

1. **Worker exited after first message**  
   - Check worker terminal for errors or exit.
   - Restart worker and re-upload; see if second message is processed.

2. **Worker still processing first message**  
   - LangGraph pipeline can take several minutes.
   - Check worker logs for `✅ LangGraph pipeline completed` before expecting the second message to be picked up.

3. **SQS FIFO deduplication**  
   - If the queue is FIFO and `MessageDeduplicationId` is not set, SQS hashes the body.
   - Bodies differ per upload; deduplication is unlikely but possible if something is wrong with the message.

4. **Connection pool / checkpointer issues**  
   - PostgresSaver uses a connection pool. After the first run, a bad connection could block the next poll.
   - Check worker logs for DB or checkpointer errors.

5. **Different queue URLs**  
   - API and worker using different `SQS_QUEUE_URL` (e.g. env vs default).

---

## 5. Recommended Test Sequence

1. **Restart worker** (clean state).
2. **Upload first document** → wait until processing completes.
3. **Immediately upload second document** (same or different file).
4. **Watch worker logs** for:
   - `Polling SQS for messages...`
   - `✅ Received 1 message(s) from SQS`
   - `📨 Received message for task: X`
5. **Run** `python3 scripts/check_sqs_queue.py` **after each upload** to see queue depth.
6. **Check** `documents` table for both documents and their `status`.

---

## 6. Code Path Reference

| Component | File | Key Lines |
|-----------|------|-----------|
| Upload → SQS | `app/main.py` | 333–356 |
| SQS send | `app/aws_services.py` | 130–174 |
| Worker poll | `app/sqs_worker.py` | 174–181 |
| Worker process | `app/sqs_worker.py` | 191–256 |
| LangGraph | `app/graph/__init__.py` | 11–44 |
