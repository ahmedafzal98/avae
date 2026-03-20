# Document Processing System — API Documentation

**Version:** 1.0.0  
**Base URL:** `https://doc-processor-frontend.fly.dev`  
**Interactive Docs:** `https://doc-processor-frontend.fly.dev/docs` (Swagger UI)

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Rate Limiting](#rate-limiting)
5. [Endpoints](#endpoints)
   - [Root](#1-root)
   - [Health](#2-health-check)
   - [Upload](#3-upload-pdf-files)
   - [Task Status](#4-get-task-status)
   - [Task Result](#5-get-task-result)
   - [Stream Result](#6-stream-task-result)
   - [List Tasks](#7-list-all-tasks)
   - [Delete Task](#8-delete-a-task)
   - [Create User](#9-create-user)
   - [Get User](#10-get-user)
   - [Login / Register](#11-login--auto-register)
   - [List Documents](#12-list-documents)
   - [Get Document](#13-get-document)
   - [Chat with Documents](#14-chat-with-documents-rag)
6. [Data Models](#data-models)
7. [Workflow Guide](#workflow-guide)

---

## Overview

This API allows you to:

- **Upload PDF files** for automated text extraction and AI summarization
- **Track processing progress** in real-time using task IDs
- **Retrieve extracted results** (text, metadata, AI summary) once processing completes
- **Chat with your documents** using RAG (Retrieval-Augmented Generation) powered by GPT-4
- **Manage users and documents** stored in the PostgreSQL database

### Processing Pipeline

```
Upload PDF  →  SQS Queue  →  Worker extracts text  →  Stores in PostgreSQL + Redis
                                                              ↓
                                             Chat endpoint queries chunks via vector search
```

---

## Authentication

Currently, the API uses **`user_id`** as a query parameter for multi-tenancy. There is no Bearer token required for most endpoints.

> **Note:** A stable `api_key` is automatically generated per user and returned on login/registration. Store it on the frontend for future reference.

---

## Error Handling

All errors return a consistent JSON structure:

```json
{
  "error": "Human-readable error message",
  "status_code": 404,
  "timestamp": "2026-02-24T10:30:00.000Z"
}
```

| HTTP Status | Meaning |
|-------------|---------|
| `200 OK` | Request succeeded |
| `201 Created` | Resource created successfully |
| `202 Accepted` | Upload accepted and queued |
| `400 Bad Request` | Invalid input (validation error, wrong file type, etc.) |
| `404 Not Found` | Resource does not exist |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Unexpected server error |
| `503 Service Unavailable` | System at capacity (queue full) |

---

## Rate Limiting

The `/upload` endpoint is rate-limited to **10 requests per minute per IP address**.  
Exceeding this limit returns `429 Too Many Requests`.

---

## Endpoints

---

### 1. Root

```
GET /
```

Returns basic API info and available links.

**Response `200 OK`**

```json
{
  "message": "Document Processing System API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

### 2. Health Check

```
GET /health
```

Returns the current system health including Redis connectivity and SQS queue depth.

**Response `200 OK`**

```json
{
  "status": "healthy",
  "redis_connected": true,
  "celery_workers": 0,
  "queue_depth": 3,
  "timestamp": "2026-02-24T10:30:00.000Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"healthy"` or `"unhealthy"` |
| `redis_connected` | `boolean` | Whether Redis is reachable |
| `celery_workers` | `integer` | Deprecated — always `0` (using SQS now) |
| `queue_depth` | `integer` | Number of messages pending in SQS queue (`-1` if SQS check failed) |
| `timestamp` | `string` | ISO 8601 datetime |

---

### 3. Upload PDF Files

```
POST /upload
Content-Type: multipart/form-data
```

Upload one or more PDF files for processing. Files are uploaded to S3 and queued in SQS for background extraction.

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_id` | `integer` | No | `1` | ID of the uploading user |
| `prompt` | `string` | No | `null` | Custom prompt to guide AI summarization |

**Form Data**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | `File[]` | Yes | One or more PDF files. Max size: **50 MB** each. Max files per request: **100** |

**Constraints**
- Only `.pdf` files are accepted
- Max file size: 50 MB per file
- Max 10 upload requests per minute per IP

**Response `202 Accepted`**

```json
{
  "task_ids": ["42", "43"],
  "total_files": 2,
  "message": "Successfully queued 2 file(s) for processing"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_ids` | `string[]` | List of task IDs — use these to track progress. Each ID corresponds to a document ID in the database. |
| `total_files` | `integer` | Number of files queued |
| `message` | `string` | Human-readable confirmation |

**Example — JavaScript/Fetch**

```javascript
const formData = new FormData();
formData.append("files", pdfFile);

const response = await fetch("https://doc-processor-frontend.fly.dev/upload?user_id=5&prompt=Summarize+key+findings", {
  method: "POST",
  body: formData,
});

const data = await response.json();
const taskId = data.task_ids[0]; // save this for polling
```

**Error Cases**

| Status | Reason |
|--------|--------|
| `400` | Non-PDF file, file too large, or too many files |
| `503` | SQS queue has more than 1000 pending messages |
| `500` | S3 upload failed or SQS message delivery failed |

---

### 4. Get Task Status

```
GET /status/{task_id}
```

Poll this endpoint to track the processing progress of an uploaded file.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | `string` | The task ID returned from the upload endpoint |

**Response `200 OK`**

```json
{
  "task_id": "42",
  "status": "PROCESSING",
  "progress": 65.0,
  "filename": "annual_report.pdf",
  "created_at": "2026-02-24T10:00:00.000Z",
  "started_at": "2026-02-24T10:00:05.000Z",
  "completed_at": null,
  "error": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `string` | The task ID |
| `status` | `string` | One of: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `progress` | `float` | Progress percentage `0–100` |
| `filename` | `string` | Original uploaded filename |
| `created_at` | `string` | ISO 8601 — when the task was created |
| `started_at` | `string \| null` | ISO 8601 — when processing started |
| `completed_at` | `string \| null` | ISO 8601 — when processing finished |
| `error` | `string \| null` | Error message if status is `FAILED` |

**Status Values**

| Status | Meaning |
|--------|---------|
| `PENDING` | Queued, not yet picked up |
| `PROCESSING` | Worker is actively extracting text |
| `COMPLETED` | Extraction finished — result is ready |
| `FAILED` | Processing failed — see `error` field |

**Recommended Polling Strategy**

Poll every 2–5 seconds until `status` is `COMPLETED` or `FAILED`.

```javascript
async function pollUntilDone(taskId) {
  while (true) {
    const res = await fetch(`https://doc-processor-frontend.fly.dev/status/${taskId}`);
    const data = await res.json();

    if (data.status === "COMPLETED") return data;
    if (data.status === "FAILED") throw new Error(data.error);

    await new Promise(r => setTimeout(r, 3000)); // wait 3s
  }
}
```

**Error Cases**

| Status | Reason |
|--------|--------|
| `404` | Task ID not found |

---

### 5. Get Task Result

```
GET /result/{task_id}
```

Retrieve the full extraction result for a **completed** task.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | `string` | The task ID returned from the upload endpoint |

**Response `200 OK`**

```json
{
  "task_id": "42",
  "filename": "annual_report.pdf",
  "page_count": 15,
  "text": "Full extracted text from the PDF document...",
  "metadata": {
    "author": "John Doe",
    "title": "Annual Report 2025",
    "creator": "Adobe Acrobat",
    "producer": "Adobe PDF Library",
    "subject": "Finance",
    "creation_date": "2025-01-15",
    "modification_date": "2025-01-20"
  },
  "extraction_time_seconds": 4.32,
  "summary": "This report covers Q4 2025 financial performance with revenue of $10.5M..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `string` | The task ID |
| `filename` | `string` | Original uploaded filename |
| `page_count` | `integer` | Number of pages in the PDF |
| `text` | `string` | Full extracted text content |
| `metadata` | `object` | PDF metadata (author, title, etc.) — may have `null` fields |
| `extraction_time_seconds` | `float` | How long the extraction took |
| `summary` | `string \| null` | AI-generated summary (only present if a `prompt` was provided at upload time) |

**Error Cases**

| Status | Reason |
|--------|--------|
| `400` | Task exists but is not yet completed |
| `404` | Task ID not found or result has expired |

---

### 6. Stream Task Result

```
GET /results/stream/{task_id}
```

Streams the task result in [NDJSON](http://ndjson.org/) format (newline-delimited JSON). Useful for large documents where loading the full result at once is impractical.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | `string` | The task ID |

**Response `200 OK`**

- `Content-Type: application/x-ndjson`
- Each line is a valid JSON object streamed progressively

**Error Cases**

| Status | Reason |
|--------|--------|
| `404` | Task ID not found |

---

### 7. List All Tasks

```
GET /tasks
```

Returns a paginated list of all tasks tracked in Redis.

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | `integer` | No | `1` | Page number (must be ≥ 1) |
| `page_size` | `integer` | No | `50` | Items per page (1–100) |

**Response `200 OK`**

```json
{
  "tasks": [
    {
      "task_id": "42",
      "status": "COMPLETED",
      "progress": 100.0,
      "filename": "report.pdf",
      "created_at": "2026-02-24T10:00:00.000Z",
      "started_at": "2026-02-24T10:00:05.000Z",
      "completed_at": "2026-02-24T10:00:12.000Z",
      "error": null
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tasks` | `TaskStatus[]` | Array of task status objects |
| `total` | `integer` | Total number of tasks across all pages |
| `page` | `integer` | Current page number |
| `page_size` | `integer` | Items per page |

**Error Cases**

| Status | Reason |
|--------|--------|
| `400` | Invalid page or page_size values |

---

### 8. Delete a Task

```
DELETE /task/{task_id}
```

Deletes a task and all associated data from Redis, PostgreSQL, and S3.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | `string` | The task ID to delete |

**Response `200 OK`**

```json
{
  "message": "Task 42 deleted successfully"
}
```

**Error Cases**

| Status | Reason |
|--------|--------|
| `404` | Task not found in either Redis or PostgreSQL |
| `500` | Failed to delete from database |

---

### 9. Create User

```
POST /users
Content-Type: application/json
```

Create a new user with a custom API key.

**Request Body**

```json
{
  "email": "alice@example.com",
  "api_key": "a-secure-32-character-api-key-here!"
}
```

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `email` | `string` | Yes | Valid email format | User's email address (must be unique) |
| `api_key` | `string` | Yes | Min 32 characters | API key for the user |

**Response `201 Created`**

```json
{
  "id": 7,
  "email": "alice@example.com",
  "api_key": "a-secure-32-character-api-key-here!",
  "created_at": "2026-02-24T10:00:00.000Z"
}
```

**Error Cases**

| Status | Reason |
|--------|--------|
| `400` | Email already exists or api_key is too short |

---

### 10. Get User

```
GET /users/{user_id}
```

Retrieve a user by their numeric ID.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `integer` | The user's numeric ID |

**Response `200 OK`**

```json
{
  "id": 7,
  "email": "alice@example.com",
  "api_key": "a-secure-32-character-api-key-here!",
  "created_at": "2026-02-24T10:00:00.000Z"
}
```

**Error Cases**

| Status | Reason |
|--------|--------|
| `404` | User not found |

---

### 11. Login / Auto-Register

```
POST /users/login
```

The recommended way to authenticate users. Provide an email address:
- If the user **already exists**, their profile is returned (login).
- If the user **does not exist**, they are automatically registered and returned.

No password is required.

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `email` | `string` | Yes | — | User's email address |
| `name` | `string` | No | `"User"` | Display name (for future use) |

**Response `200 OK`**

```json
{
  "id": 7,
  "email": "alice@example.com",
  "api_key": "7f3b8a2e1c9d0f4e6a5b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f",
  "created_at": "2026-02-24T10:00:00.000Z"
}
```

> **Important:** Store the returned `id` on the frontend — it is needed as `user_id` for all document and chat operations.

**Example — JavaScript/Fetch**

```javascript
const response = await fetch(
  `https://doc-processor-frontend.fly.dev/users/login?email=alice%40example.com`,
  { method: "POST" }
);
const user = await response.json();
localStorage.setItem("user_id", user.id);
```

---

### 12. List Documents

```
GET /documents
```

List all documents belonging to a user, with optional filtering by status.

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_id` | `integer` | No | `1` | Filter documents by user |
| `skip` | `integer` | No | `0` | Number of records to skip (offset) |
| `limit` | `integer` | No | `100` | Max records to return (max: 1000) |
| `status_filter` | `string` | No | `null` | Filter by status: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |

**Response `200 OK`**

```json
[
  {
    "id": 42,
    "user_id": 7,
    "filename": "annual_report.pdf",
    "s3_key": "uploads/42.pdf",
    "status": "COMPLETED",
    "result_text": "Extracted text content...",
    "prompt": "Summarize key financial findings",
    "summary": "Revenue grew by 15% YoY...",
    "error_message": null,
    "page_count": 15,
    "extraction_time_seconds": 4.32,
    "created_at": "2026-02-24T10:00:00.000Z",
    "started_at": "2026-02-24T10:00:05.000Z",
    "completed_at": "2026-02-24T10:00:12.000Z"
  }
]
```

**Document Object Fields**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Document ID (same as `task_id`) |
| `user_id` | `integer` | Owner's user ID |
| `filename` | `string` | Original filename |
| `s3_key` | `string` | S3 storage key |
| `status` | `string` | `PENDING` / `PROCESSING` / `COMPLETED` / `FAILED` |
| `result_text` | `string \| null` | Full extracted text (present when completed) |
| `prompt` | `string \| null` | Custom prompt provided at upload |
| `summary` | `string \| null` | AI-generated summary (if prompt was provided) |
| `error_message` | `string \| null` | Error details (if failed) |
| `page_count` | `integer \| null` | Number of pages |
| `extraction_time_seconds` | `float \| null` | Extraction duration |
| `created_at` | `string` | ISO 8601 creation timestamp |
| `started_at` | `string \| null` | ISO 8601 processing start |
| `completed_at` | `string \| null` | ISO 8601 completion time |

---

### 13. Get Document

```
GET /documents/{document_id}
```

Retrieve a single document by its ID.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_id` | `integer` | The document's numeric ID |

**Response `200 OK`**

Returns a single [Document object](#12-list-documents) (same schema as list response items).

**Error Cases**

| Status | Reason |
|--------|--------|
| `404` | Document not found |

---

### 14. Chat with Documents (RAG)

```
POST /chat?user_id={user_id}
Content-Type: application/json
```

Ask questions about your uploaded documents. Uses **Retrieval-Augmented Generation (RAG)**: your question is embedded, the most relevant document chunks are retrieved via vector similarity search, and GPT-4 generates an answer grounded in your documents.

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | `integer` | Yes | Your user ID — results are scoped to your documents only |

**Request Body**

```json
{
  "question": "What was the total revenue mentioned in the Q4 report?",
  "document_id": 42,
  "top_k": 5,
  "model": "gpt-4o"
}
```

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `question` | `string` | Yes | — | 1–1000 characters | The question to ask |
| `document_id` | `integer` | No | `null` | — | Limit search to a specific document. If omitted, searches across all your documents. |
| `top_k` | `integer` | No | `5` | 1–20 | Number of document chunks to retrieve for context |
| `model` | `string` | No | `"gpt-4o"` | — | OpenAI model to use for answer generation |

**Response `200 OK`**

```json
{
  "answer": "Based on the Q4 2025 financial report, the total revenue was $10.5 million, representing a 15% increase year-over-year.",
  "sources": [
    {
      "document_id": 42,
      "filename": "Q4_Report.pdf",
      "chunk_index": 5,
      "similarity": 0.92,
      "preview": "Q4 2025 Financial Results: Total Revenue: $10.5M, up 15% from Q4 2024..."
    }
  ],
  "chunks_found": 5,
  "model": "gpt-4o",
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 38,
    "total_tokens": 488
  },
  "error": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | `string` | AI-generated answer based strictly on retrieved document context |
| `sources` | `Source[]` | List of document chunks used as context |
| `chunks_found` | `integer` | Number of relevant chunks retrieved |
| `model` | `string \| null` | The model that generated the answer |
| `usage` | `Usage \| null` | OpenAI token usage for cost tracking |
| `error` | `string \| null` | Error description if something went wrong (non-fatal) |

**Source Object**

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | `integer` | ID of the source document |
| `filename` | `string` | Original filename of the source document |
| `chunk_index` | `integer` | Which chunk within the document (0-based) |
| `similarity` | `float` | Cosine similarity score `0.0–1.0` (higher = more relevant) |
| `preview` | `string` | Short text preview from the chunk |

**Usage Object**

| Field | Type | Description |
|-------|------|-------------|
| `prompt_tokens` | `integer` | Tokens used for the prompt (context + question) |
| `completion_tokens` | `integer` | Tokens used for the answer |
| `total_tokens` | `integer` | Total tokens consumed |

**Error Cases**

| Status | Reason |
|--------|--------|
| `400` | `user_id` not provided |
| `404` | `document_id` provided but not found or does not belong to user |
| `500` | Chat service error (OpenAI API failure, etc.) |

**Example — JavaScript/Fetch**

```javascript
const response = await fetch(`https://doc-processor-frontend.fly.dev/chat?user_id=7`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    question: "What are the key risks mentioned in the report?",
    document_id: 42,
    top_k: 5,
    model: "gpt-4o"
  }),
});

const result = await response.json();
console.log(result.answer);
console.log(result.sources); // show citations in UI
```

> **Note:** The chat endpoint only searches documents that belong to the provided `user_id`. A user cannot access or query another user's documents.

---

## Data Models

### TaskStatus

```json
{
  "task_id": "string",
  "status": "PENDING | PROCESSING | COMPLETED | FAILED",
  "progress": 0.0,
  "filename": "string",
  "created_at": "ISO8601 string",
  "started_at": "ISO8601 string | null",
  "completed_at": "ISO8601 string | null",
  "error": "string | null"
}
```

### Document

```json
{
  "id": "integer",
  "user_id": "integer",
  "filename": "string",
  "s3_key": "string",
  "status": "PENDING | PROCESSING | COMPLETED | FAILED",
  "result_text": "string | null",
  "prompt": "string | null",
  "summary": "string | null",
  "error_message": "string | null",
  "page_count": "integer | null",
  "extraction_time_seconds": "float | null",
  "created_at": "ISO8601 string",
  "started_at": "ISO8601 string | null",
  "completed_at": "ISO8601 string | null"
}
```

### User

```json
{
  "id": "integer",
  "email": "string",
  "api_key": "string",
  "created_at": "ISO8601 string"
}
```

---

## Workflow Guide

### Standard Document Upload & Query Flow

```
1. Login/Register
   POST /users/login?email=user@example.com
   → Save returned user.id

2. Upload PDF(s)
   POST /upload?user_id={id}&prompt=Summarize+this
   → Save returned task_ids[]

3. Poll for Completion
   GET /status/{task_id}   (every 3–5 seconds)
   → Wait until status === "COMPLETED"

4. Fetch Result
   GET /result/{task_id}
   → Display extracted text + summary

5. Ask Questions
   POST /chat?user_id={id}
   Body: { "question": "...", "document_id": {task_id} }
   → Display AI answer + source citations
```

### Multi-Document Chat

To ask questions across **all** of a user's documents (not just one), omit the `document_id` field from the chat request body:

```json
{
  "question": "Which documents mention regulatory compliance?",
  "top_k": 10
}
```

### Checking Document History

To list all completed documents for a user:

```
GET /documents?user_id={id}&status_filter=COMPLETED
```
