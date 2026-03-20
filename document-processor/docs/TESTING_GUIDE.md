# 🧪 Complete System Testing Guide

## 🎯 Overview

This guide walks you through testing your entire document processing and RAG chat system from scratch.

**What you'll test:**
- ✅ Database connectivity (PostgreSQL + Redis)
- ✅ HNSW vector index performance
- ✅ Document upload and processing
- ✅ RAG chat with optimized vector search
- ✅ Complete end-to-end workflow

**Time required:** 15-20 minutes

---

## 📋 Pre-Test Checklist

### **Step 1: Check Docker Services**

```bash
# Check what's running
docker ps

# Expected output:
# - doc-processor-postgres (port 5433)
# - doc-processor-redis (port 6379)
# - doc-processor-pgadmin (port 5050) - optional

# If not running, start them:
docker-compose up -d postgres redis
```

---

### **Step 2: Check Database State**

```bash
# Connect to database
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor

# Check tables and data
\dt
SELECT 
    (SELECT COUNT(*) FROM users) as users,
    (SELECT COUNT(*) FROM documents) as docs,
    (SELECT COUNT(*) FROM document_chunks) as chunks;

# Check HNSW index
\di+ document_chunks

# Exit
\q
```

---

### **Step 3: Verify HNSW Index**

```bash
cd /Users/mbp/Desktop/redis/document-processor

# Run verification script
python3 verify_hnsw_index.py
```

**Expected:**
- ✅ pgvector extension installed
- ✅ HNSW index EXISTS
- ✅ Configuration: m=16, ef_construction=64

---

## 🚀 Testing Workflow

### **TEST 1: Start All Services**

Open 3 terminals and run these commands:

**Terminal 1: FastAPI Backend**
```bash
cd /Users/mbp/Desktop/redis/document-processor
python3 -m uvicorn app.main:app --reload --port 8000

# Expected output:
# INFO: Uvicorn running on http://127.0.0.1:8000
# ✅ Database initialized successfully
```

**Terminal 2: SQS Worker**
```bash
cd /Users/mbp/Desktop/redis/document-processor
python3 -m app.sqs_worker

# Expected output:
# ✅ Connected to SQS queue
# 🔄 Polling for messages...
```

**Terminal 3: Streamlit UI**
```bash
cd /Users/mbp/Desktop/redis/document-processor
streamlit run streamlit_app.py

# Expected output:
# Local URL: http://localhost:8501
# (Browser should open automatically)
```

---

### **TEST 2: Health Check**

**Via Browser:**
```
http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "postgres": "connected",
  "redis": "connected"
}
```

**Via curl:**
```bash
curl http://localhost:8000/health | jq
```

---

### **TEST 3: Upload and Process Document**

**Via Streamlit UI:**

1. Open http://localhost:8501
2. Go to **"Upload & Process"** tab
3. Click **"Choose PDF file(s)"**
4. Select 1-2 test PDFs
5. Click **"🚀 Process All"**
6. Watch upload progress

**What to observe:**
- ✅ Upload progress bar
- ✅ Documents appear in list below
- ✅ Status changes: PENDING → PROCESSING → COMPLETED
- ✅ Page count appears
- ✅ "Ready to Chat" badge (green)

**Expected timing:**
- Upload: 1-2 seconds
- Processing: 20-40 seconds (depends on PDF size)

---

### **TEST 4: Monitor Processing**

**Watch FastAPI logs (Terminal 1):**
```bash
# Look for these log lines:
INFO: 📄 Document uploaded: filename.pdf
INFO: 📤 Message sent to SQS queue
INFO: 🚀 Starting PDF processing
INFO: ✅ Extraction complete
INFO: 📦 Created 15 chunks for document
INFO: ✅ Document ingested successfully
```

**Watch SQS Worker logs (Terminal 2):**
```bash
# Look for:
🔄 Polling for messages...
📨 Received 1 message(s)
🚀 Starting PDF processing: filename.pdf
✅ Processing completed in 23.5s
```

---

### **TEST 5: Verify Data in Database**

**Check documents:**
```bash
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT id, filename, status, page_count 
  FROM documents 
  ORDER BY created_at DESC 
  LIMIT 5;
"
```

**Check chunks:**
```bash
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT document_id, COUNT(*) as chunk_count 
  FROM document_chunks 
  GROUP BY document_id 
  ORDER BY document_id DESC;
"
```

**Expected:**
- Documents show status = 'COMPLETED'
- Each document has multiple chunks (5-50 depending on size)

---

### **TEST 6: Test RAG Chat (The Main Event!)**

**Via Streamlit UI:**

1. Wait for document status = **"Ready to Chat"**
2. Click **"💬 Chat"** button (or go to Chat tab)
3. Select your document from dropdown
4. Type a question:
   - "What is this document about?"
   - "Summarize the main points"
   - "What companies are mentioned?"
5. Press Enter and watch!

**What to observe:**
- ✅ "🤔 Thinking..." spinner appears
- ✅ AI answer appears quickly (1-2 seconds)
- ✅ Sources section shows relevant chunks
- ✅ Token usage shown at bottom

---

### **TEST 7: Verify HNSW Performance** ⚡

**Check Backend Logs (Terminal 1):**

Look for these lines:
```
INFO:app.chat_service:💬 Starting chat session
INFO:app.chat_service:🔢 Embedding question...
INFO:app.chat_service:✅ Generated question embedding
INFO:app.chat_service:🔍 Searching for top 5 similar chunks...
INFO:app.chat_service:✅ Found 5 similar chunks in 67ms ⚡
INFO:app.chat_service:📝 Building context from 5 chunks...
INFO:app.chat_service:🤖 Generating answer using gpt-4o-mini...
INFO:app.chat_service:✅ Generated answer
INFO:app.chat_service:✅ Chat completed successfully
```

**KEY LINE TO CHECK:**
```
✅ Found 5 similar chunks in 67ms ⚡
```

**Performance targets:**
- ✅ **<100ms:** Excellent! HNSW is working perfectly
- ⚠️ **100-500ms:** Good, but could be better
- ❌ **>1000ms:** Problem - index not being used

---

### **TEST 8: Verify Index Usage via SQL**

**Check query plan:**
```bash
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor

# Run this query:
EXPLAIN ANALYZE
SELECT id, chunk_index, text_content
FROM document_chunks
WHERE user_id = 1
ORDER BY embedding <=> (
    SELECT embedding FROM document_chunks WHERE user_id = 1 LIMIT 1
)
LIMIT 5;
```

**Expected output (look for this line):**
```
Index Scan using idx_chunks_embedding_hnsw on document_chunks  
(cost=... rows=5 ...)
```

**Success:** ✅ If you see "Index Scan using idx_chunks_embedding_hnsw"  
**Problem:** ❌ If you see "Seq Scan" instead

---

### **TEST 9: Performance Benchmark**

**Run automated benchmark:**
```bash
python3 verify_hnsw_index.py
```

**Expected output:**
```
============================================================
TEST 6: Performance Benchmark
============================================================

🏃 Running benchmark (5 queries)...
   Query 1: 67.23ms
   Query 2: 54.12ms
   Query 3: 58.45ms
   Query 4: 61.33ms
   Query 5: 55.67ms

📊 Results:
   Average: 59.36ms
   Min: 54.12ms
   Max: 67.23ms

✅ Excellent performance! (59ms) 🚀
```

**Performance tiers:**
- ✅ **<100ms:** Excellent
- ✅ **100-200ms:** Good
- ⚠️ **200-500ms:** Acceptable
- ❌ **>500ms:** Needs investigation

---

### **TEST 10: Multi-Document Chat**

**Test cross-document search:**

1. Upload 2-3 different PDFs
2. Wait for all to be "Ready to Chat"
3. In Chat tab, select **"All Documents"** (if you added this option)
4. Ask: "What topics are covered across my documents?"
5. Verify sources come from multiple documents

---

### **TEST 11: Edge Cases**

**Test error handling:**

1. **Empty query:**
   - Ask: "" (empty question)
   - Should show error message

2. **Gibberish query:**
   - Ask: "asdfghjkl zxcvbnm"
   - Should return "no relevant information" answer

3. **Document without chunks:**
   - Delete chunks for a document
   - Try to chat with it
   - Should handle gracefully

4. **Wrong user ID:**
   - Try to access document from different user
   - Should return no results

---

## 📊 Expected Results Summary

### **Document Processing:**

| Step | Expected Time | Success Indicator |
|------|--------------|-------------------|
| Upload | 1-2s | Progress bar completes |
| Queue | <1s | Message sent to SQS |
| Processing | 20-40s | Status → COMPLETED |
| Chunking | 2-5s | Chunks created in DB |
| Embedding | 5-10s | Embeddings stored |
| **Total** | **30-60s** | Ready to Chat ✅ |

---

### **RAG Chat:**

| Step | Expected Time | Success Indicator |
|------|--------------|-------------------|
| Embed question | 50-100ms | Question embedding created |
| **Vector search** | **50-100ms** | **HNSW index used** ⚡ |
| Build context | <10ms | Context assembled |
| LLM generation | 1-2s | Answer generated |
| **Total** | **1.5-2.5s** | Answer displayed ✅ |

---

## 🐛 Troubleshooting

### **Issue: Services won't start**

**Check Docker:**
```bash
docker-compose up -d postgres redis
docker ps

# Should show both containers running
```

**Check ports:**
```bash
lsof -i :8000  # FastAPI
lsof -i :8501  # Streamlit
lsof -i :5433  # PostgreSQL
lsof -i :6379  # Redis

# If ports are busy, kill the process or use different ports
```

---

### **Issue: "Backend server is not running"**

**Streamlit can't connect to FastAPI**

**Fix:**
```bash
# Check FastAPI is running
curl http://localhost:8000/health

# If not, start it:
python3 -m uvicorn app.main:app --reload --port 8000
```

---

### **Issue: Documents stuck in PROCESSING**

**Worker might not be running**

**Check:**
```bash
# Is worker running?
ps aux | grep sqs_worker

# Check worker logs for errors

# Restart worker:
pkill -f sqs_worker
python3 -m app.sqs_worker
```

---

### **Issue: Chat returns "no relevant information"**

**Causes:**
1. Document not processed (no chunks)
2. Question embedding failed
3. No chunks match the query

**Debug:**
```bash
# Check if chunks exist
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT document_id, COUNT(*) 
  FROM document_chunks 
  GROUP BY document_id;
"

# Check embeddings are not null
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT COUNT(*) 
  FROM document_chunks 
  WHERE embedding IS NULL;
"
# Should be 0
```

---

### **Issue: Slow vector search (>500ms)**

**HNSW index not being used**

**Fix:**
```sql
-- Update table statistics
ANALYZE document_chunks;

-- Verify index exists
SELECT indexname FROM pg_indexes 
WHERE tablename = 'document_chunks' 
AND indexname = 'idx_chunks_embedding_hnsw';

-- Check query plan
EXPLAIN ANALYZE
SELECT * FROM document_chunks
WHERE user_id = 1
ORDER BY embedding <=> (SELECT embedding FROM document_chunks LIMIT 1)
LIMIT 5;
```

---

### **Issue: OpenAI API errors**

**API key or rate limits**

**Check:**
```bash
# Verify API key in .env
cat .env | grep OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check rate limits in OpenAI dashboard
```

---

## 🎯 Complete Test Scenario

### **Scenario: Process Document and Ask Questions**

**Step-by-step:**

```bash
# 1. Ensure clean state (optional)
python3 reset_env.py --dry-run  # Check what would be deleted
python3 reset_env.py             # Reset if desired (keeps users by default)

# 2. Start Docker services
docker-compose up -d postgres redis

# 3. Verify database is ready
python3 verify_hnsw_index.py

# 4. Start FastAPI backend
python3 -m uvicorn app.main:app --reload --port 8000

# 5. Start SQS worker (new terminal)
python3 -m app.sqs_worker

# 6. Start Streamlit (new terminal)
streamlit run streamlit_app.py

# 7. Open browser
# http://localhost:8501

# 8. Upload test PDF
# - Go to "Upload & Process" tab
# - Choose a PDF file
# - Click "🚀 Process All"
# - Watch status: PENDING → PROCESSING → COMPLETED (30-60s)

# 9. Test chat
# - Click "💬 Chat" button (or go to Chat tab)
# - Select your document
# - Ask: "What is this document about?"
# - Verify response is fast (1-2s) and accurate

# 10. Check performance logs
# Look at Terminal 1 (FastAPI) for:
# "✅ Found 5 chunks in 67ms ⚡"
```

---

## 📊 Success Criteria

### **All Tests Pass When:**

| Test | Success Indicator |
|------|-------------------|
| **Docker** | Both containers running and healthy |
| **Database** | Connection successful, tables exist |
| **HNSW** | Index exists, size >0, queries use it |
| **Upload** | File uploads in 1-2s, appears in list |
| **Processing** | Completes in 30-60s, status → COMPLETED |
| **Chunks** | 5-50 chunks created per document |
| **Embeddings** | All chunks have non-null embeddings |
| **Vector Search** | Query time <200ms |
| **Chat** | Answers in 1-3s, sources shown |
| **End-to-End** | Complete workflow works smoothly |

---

## 🔍 Detailed Testing Steps

### **TEST A: Database Connectivity**

```bash
# Test PostgreSQL
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "SELECT 1;"
# Expected: Returns 1

# Test Redis
redis-cli ping
# Expected: PONG

# Test pgvector
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
"
# Expected: vector | 0.8.1 (or similar)
```

---

### **TEST B: HNSW Index Verification**

```bash
# Automated test
python3 verify_hnsw_index.py

# Manual SQL test
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
  FROM pg_indexes 
  WHERE tablename = 'document_chunks' 
  AND indexname = 'idx_chunks_embedding_hnsw';
"

# Expected:
#          indexname          |  size
# ----------------------------+---------
#  idx_chunks_embedding_hnsw | 45 MB (depends on data)
```

---

### **TEST C: Upload Endpoint (API)**

```bash
# Test via curl (alternative to Streamlit)
curl -X POST "http://localhost:8000/upload?user_id=1" \
  -F "files=@/path/to/your/test.pdf" \
  -F "files=@/path/to/another.pdf"

# Expected response:
# {
#   "message": "2 file(s) uploaded successfully",
#   "uploaded_files": [...]
# }
```

---

### **TEST D: Document Status (API)**

```bash
# Get all documents
curl "http://localhost:8000/documents?user_id=1" | jq

# Filter by status
curl "http://localhost:8000/documents?user_id=1&status_filter=COMPLETED" | jq

# Expected:
# [
#   {
#     "id": 1,
#     "filename": "test.pdf",
#     "status": "COMPLETED",
#     "page_count": 10,
#     ...
#   }
# ]
```

---

### **TEST E: Chat Endpoint (API)**

```bash
# Send chat request
curl -X POST "http://localhost:8000/chat?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this document about?",
    "document_id": 1,
    "top_k": 5
  }' | jq

# Expected response:
# {
#   "answer": "This document is about...",
#   "sources": [
#     {
#       "filename": "test.pdf",
#       "chunk_index": 2,
#       "similarity": 0.89,
#       "preview": "..."
#     }
#   ],
#   "chunks_found": 5,
#   "usage": {
#     "total_tokens": 2500
#   }
# }
```

---

### **TEST F: Vector Search Performance**

**Benchmark via Python:**
```python
import time
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Get a sample embedding
result = db.execute(text("SELECT embedding FROM document_chunks LIMIT 1"))
sample_vector = result.fetchone()[0]

# Benchmark 10 queries
times = []
for i in range(10):
    start = time.time()
    
    results = db.execute(text("""
        SELECT id, chunk_index
        FROM document_chunks
        WHERE user_id = 1
        ORDER BY embedding <=> :vec
        LIMIT 5
    """), {"vec": str(sample_vector)})
    
    _ = results.fetchall()
    elapsed_ms = (time.time() - start) * 1000
    times.append(elapsed_ms)
    print(f"Query {i+1}: {elapsed_ms:.2f}ms")

avg = sum(times) / len(times)
print(f"\nAverage: {avg:.2f}ms")
print("✅ EXCELLENT!" if avg < 100 else "✅ GOOD" if avg < 200 else "⚠️ NEEDS ATTENTION")

db.close()
```

---

### **TEST G: Multi-User Isolation**

**Test user data isolation:**

```bash
# Create test users
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"email": "test1@example.com", "api_key": "key1"}'

curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"email": "test2@example.com", "api_key": "key2"}'

# Upload docs as User 1
curl -X POST "http://localhost:8000/upload?user_id=1" \
  -F "files=@test1.pdf"

# Upload docs as User 2
curl -X POST "http://localhost:8000/upload?user_id=2" \
  -F "files=@test2.pdf"

# Verify isolation
curl "http://localhost:8000/documents?user_id=1" | jq
# Should only show User 1's documents

curl "http://localhost:8000/documents?user_id=2" | jq
# Should only show User 2's documents
```

---

## 📈 Monitoring During Testing

### **Watch All Logs in Real-Time:**

**Terminal 1 (FastAPI):**
```bash
# Watch for:
# - Upload events
# - SQS message sends
# - Chat queries
# - Vector search timings ← KEY!
```

**Terminal 2 (SQS Worker):**
```bash
# Watch for:
# - Message receives
# - Processing starts
# - Extraction progress
# - Completion status
```

**Terminal 3 (Streamlit):**
```bash
# Watch for:
# - Page loads
# - API requests
# - Any Streamlit errors
```

---

### **Database Monitoring:**

```bash
# Open another terminal for live monitoring
watch -n 2 "psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c '
  SELECT 
    status, 
    COUNT(*) as count 
  FROM documents 
  GROUP BY status 
  ORDER BY status;
'"

# This updates every 2 seconds showing document counts by status
```

---

## 🎯 Quick Validation Script

Create and run this test script:

```python
# test_system.py
import asyncio
import requests
from app.database import SessionLocal
from app.chat_service import chat_service
from app.db_utils import check_hnsw_index_exists, get_vector_search_stats

def test_health():
    """Test backend health"""
    print("1. Testing backend health...")
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("   ✅ Backend healthy")

def test_database():
    """Test database connection and index"""
    print("2. Testing database...")
    db = SessionLocal()
    
    # Check index exists
    assert check_hnsw_index_exists(db), "HNSW index not found!"
    print("   ✅ HNSW index exists")
    
    # Get stats if data exists
    stats = get_vector_search_stats(db)
    if stats['success']:
        print(f"   ✅ Index stats: {stats['times_used']} queries, {stats['index_size']}")
    
    db.close()

async def test_chat():
    """Test chat functionality"""
    print("3. Testing chat...")
    db = SessionLocal()
    
    # Check if we have any documents
    from sqlalchemy import text
    result = db.execute(text("SELECT id FROM documents WHERE status = 'COMPLETED' LIMIT 1"))
    doc = result.fetchone()
    
    if not doc:
        print("   ⚠️  No completed documents - upload a PDF first")
        db.close()
        return
    
    # Test chat
    result = await chat_service.chat(
        db=db,
        user_id=1,
        question="What is this document about?",
        document_id=doc[0]
    )
    
    assert result["answer"], "No answer generated!"
    assert len(result["sources"]) > 0, "No sources found!"
    
    print(f"   ✅ Chat working: {len(result['answer'])} char answer")
    print(f"   ✅ Sources: {result['chunks_found']} chunks found")
    
    db.close()

def main():
    print("\n" + "="*60)
    print("🧪 SYSTEM VALIDATION TEST")
    print("="*60 + "\n")
    
    try:
        test_health()
        test_database()
        asyncio.run(test_chat())
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
python3 test_system.py
```

---

## 📊 Performance Comparison Test

### **Before vs After Validation:**

If you want to test the performance improvement:

```bash
# 1. Check current performance
python3 verify_hnsw_index.py

# Should show: ~50-100ms per query

# 2. Temporarily disable index (for comparison)
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  DROP INDEX idx_chunks_embedding_hnsw;
"

# 3. Test chat query
# (via Streamlit or curl)

# Should be SLOW: 2-3 seconds

# 4. Recreate index
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  CREATE INDEX idx_chunks_embedding_hnsw 
  ON document_chunks 
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
"

# Wait for index to build (1-10 minutes depending on data size)

# 5. Test again
# Should be FAST: 50-100ms

# You'll see the 20-60x improvement!
```

---

## 🎉 Recommended Test Flow

### **Quick Test (5 minutes):**

```bash
# 1. Verify services
docker ps
python3 verify_hnsw_index.py

# 2. Start services
python3 -m uvicorn app.main:app --reload --port 8000 &
python3 -m app.sqs_worker &
streamlit run streamlit_app.py

# 3. Test in browser
# Upload PDF → Wait → Chat → Done!
```

---

### **Comprehensive Test (20 minutes):**

```bash
# 1. Clean slate
python3 reset_env.py

# 2. Verify infrastructure
docker ps
python3 verify_hnsw_index.py

# 3. Start all services
# (see above)

# 4. Upload multiple documents (3-5 PDFs)

# 5. Test various chat queries:
#    - Simple: "What is this about?"
#    - Complex: "Compare the revenue across documents"
#    - Specific: "What are the key findings?"

# 6. Monitor performance in logs

# 7. Run verification
python3 verify_hnsw_index.py

# 8. Check statistics
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT 
    indexrelname,
    idx_scan as times_used,
    pg_size_pretty(pg_relation_size(indexrelname::regclass)) as size
  FROM pg_stat_user_indexes
  WHERE indexrelname = 'idx_chunks_embedding_hnsw';
"
```

---

## 📸 Expected Screenshots

### **Streamlit Upload Tab:**
```
┌────────────────────────────────────────────┐
│ 🤖 AI Document Processor & Chat            │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ 📤 Upload & Process                  │  │
│ │                                      │  │
│ │ [Choose PDF file(s)]                 │  │
│ │ [🚀 Process All]                     │  │
│ │                                      │  │
│ │ 📄 Your Documents (12)               │  │
│ │                                      │  │
│ │ • test.pdf        ✅ Ready to Chat   │  │
│ │   10 pages • 2MB • 2 min ago        │  │
│ │   [💬 Chat]                          │  │
│ │                                      │  │
│ │ • report.pdf      ⏳ Processing 50%  │  │
│ └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

---

### **Streamlit Chat Tab:**
```
┌────────────────────────────────────────────┐
│ 💬 Chat with Data                          │
│                                            │
│ Document: [test.pdf ▼]                    │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ You:                                 │  │
│ │ What is this document about?         │  │
│ │                                      │  │
│ │ AI:                                  │  │
│ │ This document is a financial report  │  │
│ │ for Q4 2023...                       │  │
│ │                                      │  │
│ │ 📚 Sources (click to expand)         │  │
│ │ 💰 Tokens: 2,450 ($0.0004)          │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ [Type your question...]                   │
└────────────────────────────────────────────┘
```

---

### **Backend Logs (Terminal 1):**
```
INFO: Uvicorn running on http://127.0.0.1:8000
✅ Database initialized successfully
INFO:app.chat_service:💬 Starting chat session
INFO:app.chat_service:🔢 Embedding question...
INFO:app.chat_service:✅ Generated question embedding
INFO:app.chat_service:🔍 Searching for top 5 similar chunks...
INFO:app.chat_service:✅ Found 5 similar chunks in 67ms ⚡ ← KEY!
INFO:app.chat_service:🤖 Generating answer...
INFO:app.chat_service:✅ Chat completed successfully
```

---

## 🎯 Key Metrics to Watch

### **During Testing:**

| Metric | Where to Check | Target |
|--------|---------------|--------|
| Upload time | Streamlit UI | <2s |
| Processing time | Streamlit UI | 30-60s |
| Vector search | Backend logs | **<200ms** |
| Chat response | Streamlit UI | 1-3s |
| Sources found | Chat response | 3-5 chunks |
| Token usage | Chat response | 1500-3000 |

---

### **HNSW Specific:**

```bash
# Check these metrics
python3 verify_hnsw_index.py

# Target benchmarks:
# - Average query time: <100ms
# - Index size: Proportional to chunk count
# - Times used: Should increase with each query
```

---

## ✅ Final Validation Checklist

Before considering testing complete:

- [ ] Docker containers running (postgres, redis)
- [ ] HNSW index verified with `verify_hnsw_index.py`
- [ ] FastAPI backend started and healthy
- [ ] SQS worker running and polling
- [ ] Streamlit UI accessible
- [ ] Test PDF uploaded successfully
- [ ] Document processed to COMPLETED
- [ ] Chunks created in database (5-50 per doc)
- [ ] Chat query returns answer (1-3s)
- [ ] Vector search <200ms (check logs!)
- [ ] Sources displayed in chat
- [ ] No errors in any terminal

---

## 🎊 Success!

If all tests pass, your system is:
- ✅ Fully functional end-to-end
- ✅ HNSW optimized (20-60x faster)
- ✅ Production-ready
- ✅ Ready for real use!

---

## 📞 Need Help?

### **Still seeing slow queries?**
```bash
# Check query plan
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor

EXPLAIN ANALYZE
SELECT * FROM document_chunks
WHERE user_id = 1
ORDER BY embedding <=> (SELECT embedding FROM document_chunks LIMIT 1)
LIMIT 5;

# Look for "Index Scan using idx_chunks_embedding_hnsw"
```

### **Index not being used?**
```sql
-- Update statistics
ANALYZE document_chunks;

-- Verify index is valid
SELECT * FROM pg_indexes WHERE indexname = 'idx_chunks_embedding_hnsw';
```

### **Still stuck?**
- Check all 3 terminals for error messages
- Review `reset_env_*.log` files
- Run `python3 verify_hnsw_index.py` again
- Check Docker logs: `docker logs doc-processor-postgres`

---

**Created:** 2026-02-20  
**Purpose:** Complete system testing guide  
**Status:** Ready to use!

**🚀 Start testing now and enjoy the optimized performance!**
