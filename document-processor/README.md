# Document Processor — AI-Powered PDF RAG System

A production-ready document processing API that extracts text from PDFs using LlamaParse and enables semantic search and chat via RAG (Retrieval-Augmented Generation). Built with FastAPI, PostgreSQL + pgvector, Redis, AWS S3/SQS, OpenAI, and Streamlit.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         CLIENT                               │
│              (Streamlit UI / REST API / curl)                │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│   POST /upload  GET /status/:id  GET /result/:id            │
│   POST /chat    GET /documents   POST /users                 │
└──────┬──────────────────┬────────────────────────────────────┘
       │ S3 upload        │ SQS enqueue
       ▼                  ▼
┌────────────┐   ┌──────────────────┐
│  AWS S3    │   │    AWS SQS       │
│  (files)   │   │  (task queue)    │
└────────────┘   └────────┬─────────┘
                          │ poll
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                     SQS Worker                               │
│  1. Download PDF from S3                                     │
│  2. Extract text via LlamaParse                              │
│  3. Chunk text (SentenceSplitter, ~500 words, 200 overlap)  │
│  4. Generate embeddings (OpenAI text-embedding-3-small)     │
│  5. Store chunks + vectors in PostgreSQL (pgvector)          │
│  6. Cache result in Redis (1h TTL)                           │
└──────────────────────────────────────────────────────────────┘
       │                          │
       ▼                          ▼
┌─────────────────┐    ┌──────────────────────┐
│   PostgreSQL    │    │        Redis         │
│  + pgvector     │    │  (task progress +    │
│  (documents,    │    │   result cache)      │
│   chunks,       │    └──────────────────────┘
│   embeddings)   │
└─────────────────┘
```

## Tech Stack

| Layer                  | Technology                                 |
| ---------------------- | ------------------------------------------ |
| API                    | FastAPI (Python)                           |
| Database               | PostgreSQL 16 + pgvector                   |
| Cache / Queue tracking | Redis 7                                    |
| File storage           | AWS S3                                     |
| Task queue             | AWS SQS                                    |
| PDF parsing            | LlamaParse (LlamaCloud)                    |
| Embeddings             | OpenAI `text-embedding-3-small` (1536-dim) |
| Chat / RAG             | OpenAI GPT-4o                              |
| Frontend               | Streamlit                                  |
| Containers             | Docker Compose                             |

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- AWS account with S3 bucket and SQS queue configured
- [LlamaCloud API key](https://cloud.llamaindex.ai/api-key)
- [OpenAI API key](https://platform.openai.com/api-keys)

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd document-processor

cp env.example .env
# Edit .env and fill in all required values
```

### 2. Start infrastructure

```bash
docker-compose up -d postgres redis
```

Wait a few seconds for PostgreSQL to be ready, then initialize the database:

```bash
pip install -r requirements.txt
python3 -c "from app.database import init_db; init_db()"
```

Enable pgvector and create the vector index:

```bash
docker-compose exec postgres psql -U docuser -d document_processor \
  -f /docker-entrypoint-initdb.d/init.sql
```

### 3. Run the application

Open three terminals:

```bash
# Terminal 1 — API server
uvicorn app.main:app --reload --port 8000

# Terminal 2 — SQS worker (background processor)
python3 app/sqs_worker.py

# Terminal 3 — Streamlit frontend (optional)
streamlit run streamlit_app.py
```

- API docs: http://localhost:8000/docs
- Streamlit UI: http://localhost:8501
- pgAdmin: http://localhost:5050

## API Reference

### Core Endpoints

| Method   | Path                        | Description                                |
| -------- | --------------------------- | ------------------------------------------ |
| `GET`    | `/health`                   | System health check                        |
| `POST`   | `/upload`                   | Upload PDF files for processing            |
| `GET`    | `/status/{task_id}`         | Get processing status and progress         |
| `GET`    | `/result/{task_id}`         | Get extracted text and metadata            |
| `GET`    | `/results/stream/{task_id}` | Stream large results (NDJSON)              |
| `GET`    | `/tasks`                    | List all tasks (paginated)                 |
| `DELETE` | `/task/{task_id}`           | Delete task from Redis, PostgreSQL, and S3 |

### Document & User Endpoints

| Method | Path                       | Description                                 |
| ------ | -------------------------- | ------------------------------------------- |
| `POST` | `/users`                   | Create a user                               |
| `GET`  | `/users/{user_id}`         | Get user by ID                              |
| `GET`  | `/documents`               | List documents (filterable by status, user) |
| `GET`  | `/documents/{document_id}` | Get document by ID                          |

### RAG Chat Endpoint

| Method | Path    | Description                                 |
| ------ | ------- | ------------------------------------------- |
| `POST` | `/chat` | Ask questions about your uploaded documents |

**Example chat request:**

```bash
curl -X POST "http://localhost:8000/chat?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the payment terms in the contract?",
    "document_id": 5,
    "top_k": 5
  }'
```

**Example upload:**

```bash
curl -X POST "http://localhost:8000/upload?user_id=1" \
  -F "files=@/path/to/document.pdf"
```

## Database Schema

```
users
  id, email, api_key, created_at

documents
  id, user_id, filename, s3_key, status,
  result_text, page_count, summary,
  extraction_time_seconds, created_at, updated_at

document_chunks
  id, document_id, user_id, chunk_index,
  text_content, embedding (vector 1536),
  token_count, created_at
```

## Project Structure

```
document-processor/
├── app/
│   ├── main.py            # FastAPI app and all endpoints
│   ├── config.py          # Settings (loaded from .env)
│   ├── database.py        # SQLAlchemy async engine and session
│   ├── db_models.py       # ORM models (User, Document, DocumentChunk)
│   ├── schemas.py         # Pydantic models
│   ├── schemas_api.py     # API request/response schemas
│   ├── sqs_worker.py      # Background SQS polling worker
│   ├── rag_service.py     # Chunking and embedding pipeline
│   ├── chat_service.py    # Vector search + GPT-4 chat
│   ├── aws_services.py    # S3 and SQS helpers
│   ├── tasks.py           # PDF processing logic
│   ├── dependencies.py    # FastAPI dependency injection
│   ├── db_utils.py        # Database utilities
│   └── utils.py           # General utilities
├── migrations/
│   ├── 001_enable_pgvector.sql
│   ├── 001_add_hnsw_vector_index.sql
│   └── run_migration.py
├── scripts/
│   └── migrate_redis_to_pg.py
├── tests/
│   ├── quick_test.py
│   ├── load_test.py
│   └── test_upload.py
├── docs/                  # Additional documentation
├── storage/uploads/       # Local file cache (gitignored)
├── streamlit_app.py       # Streamlit frontend
├── docker-compose.yml     # PostgreSQL, Redis, pgAdmin
├── init.sql               # DB initialization (pgvector extension)
├── requirements.txt       # Python dependencies
└── env.example            # Environment variable template
```

## Multi-Tenancy

Every document and chunk stores a `user_id`. All queries are scoped to the requesting user — users cannot access each other's documents or chunks.

## Environment Variables

Copy `env.example` to `.env` and fill in all values. Required variables:

| Variable                   | Description                        |
| -------------------------- | ---------------------------------- |
| `AWS_ACCESS_KEY_ID`        | AWS credentials                    |
| `AWS_SECRET_ACCESS_KEY`    | AWS credentials                    |
| `AWS_REGION`               | AWS region (e.g. `us-east-1`)      |
| `S3_BUCKET_NAME`           | S3 bucket for PDF storage          |
| `SQS_QUEUE_URL`            | SQS queue URL for task processing  |
| `LLAMA_CLOUD_API_KEY`      | LlamaCloud key for PDF parsing     |
| `OPENAI_API_KEY`           | OpenAI key for embeddings and chat |
| `POSTGRES_PASSWORD`        | PostgreSQL password                |
| `PGADMIN_DEFAULT_PASSWORD` | pgAdmin password                   |

## Common Issues

| Error                               | Fix                                          |
| ----------------------------------- | -------------------------------------------- |
| `Extension "vector" does not exist` | Run `CREATE EXTENSION vector;` as superuser  |
| `OpenAI API key not found`          | Add `OPENAI_API_KEY` to `.env`               |
| `Connection refused` on port 5433   | Run `docker-compose up -d postgres`          |
| `No chunks created`                 | Check LlamaParse logs in the worker output   |
| Slow vector search                  | Ensure HNSW index exists (see `migrations/`) |

## Data Handling & Compliance

### Data We Process

- **Uploaded documents**: PDFs (regulatory filings, certificates, etc.)
- **Extracted data**: Structured fields (company numbers, addresses, etc.) from documents
- **Verification results**: Audit logs with extracted vs API comparison
- **User data**: Email, auth tokens (via Clerk)

### Storage & Retention

| Data type      | Location     | Retention                                                                 |
| -------------- | ------------ | ------------------------------------------------------------------------- |
| Documents      | AWS S3       | Retained until explicitly deleted. Future: S3 Lifecycle Policy (24–48h after workflow completion). |
| Audit logs     | PostgreSQL   | Retained for compliance (configurable).                                    |
| Document chunks| PostgreSQL   | Retained with document; deleted when document is deleted.                  |
| Task status    | Redis        | TTL: 1 hour.                                                              |

### Data Deletion

- Users can request deletion of documents via `DELETE /task/{task_id}`.
- On deletion: S3 objects removed, PostgreSQL records purged, Redis keys expired.
- Audit logs may be retained for regulatory compliance even after document deletion.

### UK GDPR & Data Protection

- We process personal data in accordance with UK GDPR and the Data Protection Act 2018.
- **Lawful basis**: Contract performance / legitimate interest for compliance verification.
- **Data subject rights**: Access, rectification, erasure, portability, objection.
- **Data transfers**: Host in AWS `eu-west-2` (London) for UK data residency where required.
- **Sub-processors**: AWS (S3, SQS), OpenAI (embeddings, extraction), LlamaCloud (PDF parsing), Clerk (auth). Each has appropriate data processing agreements.

### Security

- **Encryption in transit**: TLS 1.2+
- **Encryption at rest**: AWS default (S3, RDS)
- **Access control**: Authentication via Clerk; user-scoped queries
- **Audit trail**: Verification decisions and HITL actions logged in `audit_logs`

For data protection enquiries, contact your system administrator.

## Demo sample PDFs

Bundled PDFs for **Vision POC** demos live in [`samples/demo/`](samples/demo/README.md):

- **Eng-Arabic.pdf** — English / Arabic mixed document  
- **809508119-Iqama.pdf** — residence permit–style card (scanned/image-heavy)

Upload with `audit_target=vision_poc` and run the **SQS worker** so jobs complete. Quick upload:

```bash
cd document-processor
chmod +x scripts/upload_demo_pdfs.sh   # once
./scripts/upload_demo_pdfs.sh
```

## License

MIT
