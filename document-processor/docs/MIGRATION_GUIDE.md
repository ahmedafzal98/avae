# PostgreSQL + Redis Hybrid Database Migration Guide

## Overview

This document describes the hybrid database architecture implementation that combines PostgreSQL for persistent data storage with Redis for caching and real-time operations.

## Architecture

### PostgreSQL (Persistent Storage)
- **Users**: API users and authentication
- **Documents**: Document metadata, processing status, and results

### Redis (Cache & Real-time)
- Task queuing and progress tracking
- Rate limiting
- Temporary results cache

## Files Created

### 1. Database Configuration (`app/database.py`)
- SQLAlchemy 2.0 engine setup
- Session management with connection pooling
- `get_db()` dependency for FastAPI
- `init_db()` function to create tables

### 2. Database Models (`app/db_models.py`)
- **User Model**: 
  - `id` (primary key)
  - `email` (unique, indexed)
  - `api_key` (unique, indexed)
  - `created_at`
  - Relationship: One-to-Many with Documents

- **Document Model**:
  - `id` (primary key)
  - `user_id` (foreign key)
  - `filename`, `s3_key`
  - `status` (PENDING, PROCESSING, COMPLETED, FAILED)
  - `result_text` (extracted content)
  - `error_message`
  - `page_count`, `extraction_time_seconds`
  - Timestamps: `created_at`, `started_at`, `completed_at`
  - Indexes on: `user_id + status`, `created_at`

### 3. Pydantic Schemas (`app/schemas.py`)
- **User Schemas**: `UserCreate`, `UserUpdate`, `UserResponse`, `UserWithDocuments`
- **Document Schemas**: `DocumentCreate`, `DocumentUpdate`, `DocumentResponse`, `DocumentWithUser`
- **List Schemas**: `DocumentListResponse`
- All schemas use Pydantic v2 with `ConfigDict(from_attributes=True)`

### 4. Updated Configuration (`app/config.py`)
- Added PostgreSQL connection settings:
  - `postgres_host`, `postgres_port`
  - `postgres_db`, `postgres_user`, `postgres_password`
- Added `database_url` property for SQLAlchemy
- Added `debug_sql` flag for query logging

### 5. Migration Script (`scripts/migrate_redis_to_pg.py`)
- Migrates existing Redis data to PostgreSQL
- Features:
  - Scans Redis for all `task:*` keys
  - Creates default user for migrated documents
  - Handles result data from `result:*` keys
  - Skips temporary keys (progress:*)
  - Prevents duplicate migrations
  - Provides detailed statistics and progress reporting
  - Supports `--dry-run` mode for testing

### 6. File Reorganization
- Renamed `app/models.py` → `app/schemas_api.py`
- Updated all imports across the codebase

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    s3_key VARCHAR(512) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    result_text TEXT,
    error_message TEXT,
    page_count INTEGER,
    extraction_time_seconds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_user_status ON documents(user_id, status);
CREATE INDEX idx_created_at ON documents(created_at);
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `sqlalchemy>=2.0.25`
- `psycopg2-binary==2.9.9`
- `alembic==1.13.1`

### 2. Start PostgreSQL

Using Docker Compose (already configured):

```bash
docker-compose up -d postgres
```

The database will be available at:
- Host: `127.0.0.1` (or `localhost`)
- Port: `5433` (mapped to avoid conflict with local PostgreSQL on 5432)
- Database: `document_processor`
- User: `docuser`
- Password: `docpass_dev_2026`

### 3. Initialize Database

The database tables are automatically created on application startup via the `startup_event` in `main.py`.

Alternatively, you can manually initialize:

```python
from app.database import init_db
init_db()
```

### 4. Migrate Existing Data

To migrate existing Redis data to PostgreSQL:

```bash
# Test migration (dry-run)
python scripts/migrate_redis_to_pg.py --dry-run

# Run actual migration
python scripts/migrate_redis_to_pg.py
```

Migration features:
- Creates a default user: `migrated@system.local`
- Migrates all task metadata to documents table
- Preserves timestamps and status
- Migrates extracted text from results
- Skips already migrated documents
- Provides detailed progress and statistics

## Usage Examples

### Using Database Sessions in FastAPI

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.db_models import User, Document
from app.schemas import DocumentResponse

@app.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
```

### Creating Records

```python
from app.db_models import User, Document

# In an endpoint with db: Session = Depends(get_db)
user = User(email="user@example.com", api_key="secret_key")
db.add(user)
db.commit()
db.refresh(user)

document = Document(
    user_id=user.id,
    filename="document.pdf",
    s3_key="uploads/abc123.pdf",
    status="PENDING"
)
db.add(document)
db.commit()
```

### Querying with Relationships

```python
# Get user with all documents
user = db.query(User).filter(User.id == user_id).first()
for doc in user.documents:
    print(doc.filename, doc.status)

# Get document with user
document = db.query(Document).filter(Document.id == doc_id).first()
print(document.user.email)
```

## Configuration

Add these to your `.env` file:

```env
# PostgreSQL
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=document_processor
POSTGRES_USER=docuser
POSTGRES_PASSWORD=docpass_dev_2026

# Debug (optional)
DEBUG_SQL=false
```

## Key Features

### SQLAlchemy 2.0 Syntax
- Uses `Mapped[type]` type hints
- Uses `mapped_column()` for column definitions
- Modern relationship() definitions

### Connection Pooling
- QueuePool with 10 base connections
- Max overflow of 20 connections
- Pre-ping to verify connections

### Pydantic v2 Integration
- `ConfigDict(from_attributes=True)` for ORM models
- Type-safe schemas with validation
- Automatic JSON serialization

### Relationships
- One-to-Many: User → Documents
- Cascade delete: Deleting user deletes all documents
- Bidirectional navigation

### Indexes
- Email and API key (unique, indexed)
- User ID (indexed)
- Status (indexed)
- Composite index on (user_id, status)
- Created_at timestamp (indexed)

## Next Steps

1. **Add Authentication**: Implement API key validation using the User model
2. **Update Endpoints**: Modify existing endpoints to use PostgreSQL for persistence
3. **Add User Management**: Create endpoints for user CRUD operations
4. **Implement Pagination**: Use SQLAlchemy's offset/limit for document listings
5. **Add Search**: Implement full-text search on result_text
6. **Set up Alembic**: For database schema migrations in production

## Testing

Test database connection:

```python
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.fetchone())
```

## Troubleshooting

### Connection Issues
- Ensure PostgreSQL is running: `docker-compose ps`
- Check credentials in `.env` match `docker-compose.yml`
- Verify network connectivity: `psql -h localhost -U docuser -d document_processor`

### Migration Issues
- Run with `--dry-run` first to test
- Check Redis connection: `redis-cli ping`
- Verify Redis has data: `redis-cli keys "task:*"`

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: Python 3.8+ required

## Architecture Benefits

1. **Data Persistence**: PostgreSQL ensures data survives Redis restarts
2. **ACID Compliance**: Transactions ensure data consistency
3. **Relationships**: Proper foreign keys and referential integrity
4. **Scalability**: Separate read-heavy (Redis) from write-heavy (PostgreSQL) operations
5. **Query Power**: Complex queries, joins, and aggregations
6. **Full-text Search**: Native PostgreSQL text search capabilities
7. **Backup & Recovery**: Standard PostgreSQL backup tools
