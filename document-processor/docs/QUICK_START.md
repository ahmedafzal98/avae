# 🚀 Quick Start Guide - PostgreSQL Integration

## ✅ Prerequisites

- ✅ PostgreSQL running (port 5433)
- ✅ Redis running (port 6379)
- ✅ Python dependencies installed

---

## 🎬 Start Everything

### **Option 1: All-in-One (Recommended)**

```bash
cd /Users/mbp/Desktop/redis/document-processor

# Start databases
docker-compose up -d postgres redis

# Wait 3 seconds for databases to be ready
sleep 3

# Start API (Terminal 1)
uvicorn app.main:app --reload --port 8000

# Start Worker (Terminal 2 - open new terminal)
python3 app/sqs_worker.py
```

### **Option 2: Step-by-Step**

```bash
# Terminal 1: Databases
docker-compose up postgres redis

# Terminal 2: API
cd /Users/mbp/Desktop/redis/document-processor
uvicorn app.main:app --reload

# Terminal 3: Worker
cd /Users/mbp/Desktop/redis/document-processor
python3 app/sqs_worker.py
```

---

## 🧪 Test the Integration

### **1. Upload a PDF**

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "files=@/path/to/your/document.pdf"
```

**Expected Response:**
```json
{
  "task_ids": ["1"],
  "total_files": 1,
  "message": "Successfully queued 1 file(s) for processing"
}
```

### **2. Check Status**

```bash
curl "http://localhost:8000/status/1"
```

**Expected Response:**
```json
{
  "task_id": "1",
  "status": "PROCESSING",
  "progress": 45.0,
  "filename": "document.pdf",
  "created_at": "2026-02-16T10:30:00",
  ...
}
```

### **3. Get Result (when completed)**

```bash
curl "http://localhost:8000/result/1"
```

**Expected Response:**
```json
{
  "task_id": "1",
  "filename": "document.pdf",
  "page_count": 5,
  "text": "Extracted PDF content here...",
  "extraction_time_seconds": 12.34,
  ...
}
```

---

## 🗄️ Check PostgreSQL

### **Connect to Database:**

```bash
docker-compose exec postgres psql -U docuser -d document_processor
```

### **Useful Queries:**

```sql
-- See all tables
\dt

-- View users
SELECT * FROM users;

-- View documents
SELECT id, filename, status, created_at FROM documents;

-- Count by status
SELECT status, COUNT(*) FROM documents GROUP BY status;

-- Recent documents
SELECT id, filename, status, created_at 
FROM documents 
ORDER BY created_at DESC 
LIMIT 10;

-- Documents with extracted text
SELECT id, filename, LEFT(result_text, 100) as preview
FROM documents 
WHERE result_text IS NOT NULL;

-- Exit
\q
```

---

## 🔍 Check Redis

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Check keys
KEYS task:*
KEYS result:*

# View task data
HGETALL task:1

# View result (if not expired)
GET result:1

# Exit
exit
```

---

## 📊 Use the API Docs

Open in browser:
```
http://localhost:8000/docs
```

You'll see:
- ✅ All endpoints
- ✅ Try them interactively
- ✅ See request/response schemas
- ✅ Test authentication

---

## 🆕 New Endpoints

### **Create User**
```bash
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "api_key": "your_32_character_api_key_here_12345"
  }'
```

### **Get User**
```bash
curl "http://localhost:8000/users/1"
```

### **List Documents**
```bash
# All documents
curl "http://localhost:8000/documents"

# Filter by status
curl "http://localhost:8000/documents?status_filter=COMPLETED"

# Pagination
curl "http://localhost:8000/documents?skip=0&limit=10"
```

### **Get Document**
```bash
curl "http://localhost:8000/documents/1"
```

---

## 🐛 Troubleshooting

### **"Connection refused" error:**
```bash
# Check if databases are running
docker-compose ps

# Should show:
# doc-processor-postgres  Up
# doc-processor-redis     Up

# If not, start them:
docker-compose up -d postgres redis
```

### **"Table doesn't exist" error:**
```bash
# Check if tables were created
docker-compose exec postgres psql -U docuser -d document_processor -c "\dt"

# If no tables, restart API (it creates tables on startup)
# Ctrl+C to stop, then:
uvicorn app.main:app --reload
```

### **Worker not processing:**
```bash
# Check SQS queue
# Check worker logs for errors
# Verify AWS credentials in .env file
```

### **Can't see data in PostgreSQL:**
```bash
# Verify you're on the right port
docker-compose exec postgres psql -U docuser -d document_processor

# Check if data exists
SELECT COUNT(*) FROM documents;
```

---

## 🎯 What to Expect

### **After Upload:**
1. ✅ Document record created in PostgreSQL (status="PENDING")
2. ✅ Task metadata created in Redis
3. ✅ Message sent to SQS
4. ✅ Returns task_id (= PostgreSQL document ID)

### **During Processing:**
1. ✅ Worker picks up message from SQS
2. ✅ Updates PostgreSQL: status="PROCESSING"
3. ✅ Updates Redis: progress 0% → 100%
4. ✅ Downloads PDF from S3
5. ✅ Extracts text, tables, images

### **After Completion:**
1. ✅ Saves result to Redis (1 hour TTL)
2. ✅ Saves result to PostgreSQL (permanent)
3. ✅ Updates status="COMPLETED"
4. ✅ User can retrieve result anytime

---

## 📈 Monitoring

### **Check API Health:**
```bash
curl "http://localhost:8000/health"
```

### **Check Worker Logs:**
```bash
# Worker prints progress:
📨 Received message for task: 1
🚀 Starting PDF processing: document.pdf
📊 Task 1: 10% complete
📊 Task 1: 50% complete
✅ Completed processing document.pdf in 12.34s
💾 Saved result to PostgreSQL (document_id=1)
```

### **Check Database Size:**
```sql
SELECT 
    pg_size_pretty(pg_database_size('document_processor')) as db_size;
```

---

## 🎉 Success Indicators

You know it's working when:

1. ✅ Upload returns task_id
2. ✅ Status shows "PROCESSING" with progress
3. ✅ Worker logs show processing activity
4. ✅ PostgreSQL has document records
5. ✅ Result endpoint returns extracted text
6. ✅ Data persists after Redis restart

---

## 🚀 You're Ready!

Your hybrid PostgreSQL + Redis architecture is now live!

- Fast real-time updates ⚡
- Permanent data storage 💾
- Scalable architecture 📈
- Production-ready 🎯

Happy coding! 🎉
