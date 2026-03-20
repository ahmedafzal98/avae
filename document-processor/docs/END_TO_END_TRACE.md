# End-to-End Document Processing Trace

This document traces the complete lifecycle of a document from upload to processed result, with verification points for Redis, SQS, and the background worker.

---

## 1. UPLOAD PHASE (FastAPI)

**Entry point:** `POST /upload` → `upload_files()` in `app/main.py` (lines 154–364)

### Flow

```
User uploads PDF
    ↓
upload_files() [main.py:158]
    ↓
1. S3: aws_services.upload_file_to_s3() [main.py:271]
    ↓
2. PostgreSQL: Create Document record [main.py:294-311]
    ↓
3. Redis: redis_client.hset() + rpush() [main.py:331-332]
    ↓
4. SQS: aws_services.send_message_to_sqs() [main.py:346-349]
    ↓
Return 202 Accepted with task_ids
```

### Functions and locations

| Step | Function / Call | File | Purpose |
|------|-----------------|------|---------|
| S3 upload | `aws_services.upload_file_to_s3()` | `app/aws_services.py:33-62` | Store PDF in S3 |
| DB record | `Document` creation + `db.commit()` | `app/main.py:294-311` | Create document row |
| Redis write | `redis_client.hset(f"task:{task_id}", mapping=task_data)` | `app/main.py:331` | Task metadata |
| Redis list | `redis_client.rpush("all_tasks", task_id)` | `app/main.py:332` | Add to task list |
| SQS send | `aws_services.send_message_to_sqs()` | `app/main.py:346-349` | Enqueue job |

---

## 2. VERIFYING REDIS WRITE

### Current behavior

- `redis_client.hset()` and `redis_client.rpush()` are called without checking return values.
- Redis errors would surface as exceptions, but there is no explicit verification step.

### How to verify Redis

**Option A: Read back after write**

```python
# After redis_client.hset() and rpush()
stored = redis_client.hgetall(f"task:{task_id}")
if not stored or stored.get("task_id") != task_id:
    raise HTTPException(status_code=500, detail="Redis write verification failed")
```

**Option B: Use `/status/{task_id}`**

- After upload, call `GET /status/{task_id}`.
- If it returns 200 with `status: "PENDING"`, Redis has the task.

**Option C: Redis keys**

- Task hash: `task:{task_id}`
- Task list: `all_tasks`
- Check with: `redis-cli HGETALL task:123` and `redis-cli LRANGE all_tasks 0 -1`

**Option D: Add explicit verification in upload flow**

Add after `redis_client.rpush("all_tasks", task_id)` in `main.py`:

```python
# Verify Redis write (add: import redis)
try:
    stored = redis_client.hgetall(f"task:{task_id}")
    if not stored or str(stored.get("task_id")) != task_id:
        logger.error(f"Redis verification failed for task {task_id}")
        raise HTTPException(status_code=500, detail="Failed to store task metadata")
except Exception as e:
    logger.error(f"Redis verification error: {e}")
    raise HTTPException(status_code=500, detail="Redis storage verification failed")
```

---

## 3. VERIFYING SQS PUSH

### Current behavior

- `aws_services.send_message_to_sqs()` returns `message_id` or `None`.
- If `None`, upload raises `HTTPException(500)` and the request fails.

```python
# main.py:346-358
message_id = aws_services.send_message_to_sqs(
    message_body=sqs_message,
    message_attributes={"task_id": task_id}
)
if not message_id:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to queue {file.filename} for processing"
    )
```

### How to verify SQS

- **API response:** 202 with `task_ids` means SQS send succeeded.
- **Queue depth:** `python3 scripts/check_sqs_queue.py` shows waiting and in-flight messages.
- **AWS console:** SQS queue → “Send and receive messages” / metrics.

---

## 4. WORKER ACTIVATION

### Entry point

**Command:** `python -m app.sqs_worker`

**File:** `app/sqs_worker.py`

**Execution path:**

```
python -m app.sqs_worker
    ↓
if __name__ == "__main__": [sqs_worker.py:282-286]
    ↓
worker_loop() [sqs_worker.py:152]
```

### Function that starts the worker

| Function | Location | Role |
|----------|----------|------|
| `worker_loop()` | `app/sqs_worker.py:152` | Main loop; polls SQS and processes messages |

---

## 5. MESSAGE PULL FROM SQS

### Function that pulls messages

| Function | Location | Role |
|----------|----------|------|
| `aws_services.receive_messages_from_sqs()` | `app/aws_services.py:176-224` | Long-poll SQS and return messages |

**Called from:** `worker_loop()` at `sqs_worker.py:175-179`

```python
messages = aws_services.receive_messages_from_sqs(
    max_messages=1,
    wait_time_seconds=20,
    visibility_timeout=900  # 15 minutes
)
```

### Verifying the pull

- Log: `✅ Received {n} message(s) from SQS` (aws_services.py:219)
- Log: `📨 Received message for task: {task_id}` (sqs_worker.py:216)

---

## 6. DOCUMENT PROCESSING ENTRY POINT

### Function that starts processing

| Function | Location | Role |
|----------|----------|------|
| `process_pdf_from_s3()` | `app/sqs_worker.py:76` | Entry point for processing a single PDF |

**Called from:** `worker_loop()` at `sqs_worker.py:235-237`

```python
success = process_pdf_from_s3(
    task_id, s3_bucket, s3_key, filename, prompt, audit_target
)
```

---

## 7. WORKER COMPONENT BREAKDOWN

### 7.1 `worker_loop()` — main loop

**File:** `app/sqs_worker.py:152-279`

| Responsibility | Code |
|----------------|------|
| Signal handlers | `signal.signal(SIGINT/SIGTERM)` |
| Poll SQS | `aws_services.receive_messages_from_sqs()` |
| Parse message | `body`, `receipt_handle`, `receive_count` |
| Validate format | `task_id`, `s3_bucket`, `s3_key`, `filename` |
| Validate task_id | `_is_valid_task_id()` (numeric) |
| Process | `process_pdf_from_s3()` |
| Success | `aws_services.delete_message_from_sqs(receipt_handle)` |
| Poison handling | Delete after 3+ failures |

### 7.2 `process_pdf_from_s3()` — processing orchestrator

**File:** `app/sqs_worker.py:76-148`

| Step | Action |
|------|--------|
| 1 | Set Redis status to `PROCESSING` |
| 2 | Call `update_task_progress(task_id, 0, "PROCESSING")` |
| 3 | Call `run_avae_graph()` (LangGraph pipeline) |
| 4 | On success: return `True` |
| 5 | On error: set Redis/PostgreSQL to `FAILED`, return `False` |

### 7.3 Helper functions

| Function | Location | Purpose |
|----------|----------|---------|
| `_is_valid_task_id()` | sqs_worker.py:39-46 | Ensure task_id is numeric |
| `update_task_progress()` | sqs_worker.py:49-73 | Update Redis + PostgreSQL progress |
| `signal_handler()` | sqs_worker.py:32-36 | Graceful shutdown |

---

## 8. LANGGRAPH PIPELINE (document processing)

### Entry point

| Function | Location | Role |
|----------|----------|------|
| `run_avae_graph()` | `app/graph/__init__.py:11-44` | Invoke graph with initial state |

**Called from:** `process_pdf_from_s3()` at `sqs_worker.py:108-116`

### Graph structure

**File:** `app/graph/graph.py`

```
burst_pdf → [classify_pages | handle_error]
    ↓
classify_pages → extract_parallel → merge_extractions → normalize
    ↓
fetch_api → verify → route_hitl
    ↓
[persist | human_review → persist]
```

### Node-by-node

| Node | File | Function | Purpose |
|------|------|----------|---------|
| **burst_pdf** | nodes.py:59 | `burst_pdf()` | Download from S3, burst PDF into pages (PyMuPDF) |
| **classify_pages** | nodes.py:149 | `classify_pages()` | Classify pages: text, image, table, chart |
| **extract_parallel** | nodes.py:203 | `extract_parallel()` | Extract text per page (Textract, VLM, PyMuPDF) |
| **merge_extractions** | nodes.py:276 | `merge_extractions()` | Merge page extractions into one text |
| **normalize** | nodes.py:303 | `normalize()` | LLM structured extraction |
| **fetch_api** | nodes.py:312 | `fetch_api()` | Fetch ground truth (Companies House, Land Registry, etc.) |
| **verify** | nodes.py:335 | `verify()` | Compare extracted vs API |
| **route_hitl** | nodes.py:349 | `route_hitl()` | Route to persist or human_review |
| **human_review** | nodes.py:357 | `human_review()` | Build HITL checkpoint and preview |
| **persist** | nodes.py:434 | `persist()` | Save to audit_logs, Document, Redis |
| **handle_error** | nodes.py:305 | `handle_error()` | Set status to FAILED in Redis/PostgreSQL |

### Progress updates in the graph

| Node | Progress % |
|------|------------|
| burst_pdf | 0 |
| extract_parallel | 20 |
| extract_parallel (after) | 40 |
| persist | 70 |
| persist (final) | 100 |

---

## 9. END-TO-END TRACE SUMMARY

```
┌─────────────────────────────────────────────────────────────────────────┐
│ UPLOAD (FastAPI)                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ upload_files() → S3 → PostgreSQL → Redis → SQS → 202 + task_ids          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ WORKER (python -m app.sqs_worker)                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ worker_loop()                                                            │
│   → receive_messages_from_sqs()  [PULL]                                 │
│   → process_pdf_from_s3()        [PROCESS ENTRY]                        │
│       → run_avae_graph()         [LANGGRAPH]                            │
│           burst_pdf → classify → extract → merge → normalize             │
│           → fetch_api → verify → route_hitl → [persist | human_review]  │
│   → delete_message_from_sqs()    [ACK on success]                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. VERIFICATION CHECKLIST

| Check | How |
|-------|-----|
| Redis has task | `GET /status/{task_id}` or `redis-cli HGETALL task:{id}` |
| SQS received job | 202 response + `message_id`; `scripts/check_sqs_queue.py` |
| Worker running | Process list: `ps aux \| grep sqs_worker` |
| Worker pulled message | Log: `📨 Received message for task: {task_id}` |
| Processing started | Log: `🚀 Starting LangGraph pipeline` |
| Processing finished | Log: `✅ LangGraph pipeline completed` or `✅ Persisted` |
| Message deleted | Log: `✅ Message processed and deleted from SQS` |

---

## 11. FILES REFERENCE

| File | Role |
|------|------|
| `app/main.py` | Upload API, status, results |
| `app/aws_services.py` | S3 and SQS operations |
| `app/sqs_worker.py` | Worker loop and `process_pdf_from_s3` |
| `app/graph/__init__.py` | `run_avae_graph` |
| `app/graph/graph.py` | Graph definition |
| `app/graph/nodes.py` | All pipeline nodes |
| `app/dependencies.py` | Redis client |
| `scripts/check_sqs_queue.py` | SQS queue check |
