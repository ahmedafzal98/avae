# 📊 Data Source Guide - Where UI Data Comes From

## Overview

Your Streamlit UI displays data from **3 primary sources**:
1. **Redis** - Fast, real-time data (24h TTL)
2. **PostgreSQL** - Permanent storage (forever)
3. **AWS S3** - PDF file storage (not directly displayed in UI)

**AWS SQS** is used for job queuing but not displayed in UI.

---

## 🎯 Complete Data Flow Map

### **1. 📊 All Tasks Page**

When you view the **"📊 All Tasks"** page, here's where each piece of data comes from:

```
┌──────────────────────────────────────────────────────┐
│              📊 All Tasks Page                       │
├──────────────────────────────────────────────────────┤
│ Total: 5  │  Completed: 3  │  Processing: 1  │ ...  │ ← Redis
├──────────────────────────────────────────────────────┤
│ document.pdf  │ ✅ COMPLETED │ 100% │ 👁️ │ 🗑️     │
│    ↓              ↓            ↓                     │
│  Redis         Redis         Redis                   │
└──────────────────────────────────────────────────────┘
```

**Data Source:** 🟢 **Redis Only**

**API Endpoint:** `GET /tasks`

**Backend Code:**
```python
# app/main.py - Line 428
total = redis_client.llen("all_tasks")

# app/main.py - Lines 435-440
task_ids = redis_client.lrange("all_tasks", start_idx, end_idx)
for task_id in task_ids:
    task_data = redis_client.hgetall(f"task:{task_id}")
```

**What's Fetched from Redis:**
- `task_id` - Task identifier
- `status` - PENDING, PROCESSING, COMPLETED, FAILED
- `progress` - 0-100%
- `filename` - Original PDF filename
- `created_at` - Upload timestamp
- `started_at` - Processing start time
- `completed_at` - Processing end time
- `error` - Error message (if failed)

**Redis Keys Used:**
- `all_tasks` (list) - All task IDs
- `task:{task_id}` (hash) - Task metadata

---

### **2. 👁️ View Button → Task Status Display**

When you **click "View" button** and see task details:

```
┌──────────────────────────────────────────────────────┐
│           📊 Current Task Status                     │
├──────────────────────────────────────────────────────┤
│ Task ID: 10  │ Status: ✅ COMPLETED │ Progress: 100%│
│    ↓              ↓                       ↓          │
│  Redis         Redis                   Redis         │
├──────────────────────────────────────────────────────┤
│ File: document.pdf  ← Redis                          │
├──────────────────────────────────────────────────────┤
│ [██████████████████████████████ 100%]  ← Redis      │
├──────────────────────────────────────────────────────┤
│ ⏰ Timeline                                          │
│ Created: 2026-02-17 10:30:15  ← Redis               │
│ Started: 2026-02-17 10:30:18  ← Redis               │
│ Completed: 2026-02-17 10:30:25  ← Redis             │
└──────────────────────────────────────────────────────┘
```

**Data Source:** 🟢 **Redis Only**

**API Endpoint:** `GET /status/{task_id}`

**Backend Code:**
```python
# app/main.py - Line 298
task_data = redis_client.hgetall(f"task:{task_id}")
```

**What's Displayed:**
| UI Element | Data Source | Redis Key | Field |
|------------|-------------|-----------|-------|
| Task ID | Redis | `task:{task_id}` | `task_id` |
| Status Badge | Redis | `task:{task_id}` | `status` |
| Progress % | Redis | `task:{task_id}` | `progress` |
| Filename | Redis | `task:{task_id}` | `filename` |
| Created At | Redis | `task:{task_id}` | `created_at` |
| Started At | Redis | `task:{task_id}` | `started_at` |
| Completed At | Redis | `task:{task_id}` | `completed_at` |
| Error Message | Redis | `task:{task_id}` | `error` |

---

### **3. 📥 View Results → Extraction Results**

When you **click "View Results"** button:

```
┌──────────────────────────────────────────────────────┐
│              📥 Extraction Results                   │
├──────────────────────────────────────────────────────┤
│ Pages: 5  │ Characters: 15,234 │ Tables: 3 │ Time: 12.4s│
│    ↓            ↓                   ↓           ↓    │
│  Redis      Redis (or PG)        Redis      Redis    │
├──────────────────────────────────────────────────────┤
│ [📝 Text] [📊 Tables] [🖼️ Images] [📋 Metadata]     │
└──────────────────────────────────────────────────────┘
```

**Data Source:** 🟢 **Redis First**, 🔵 **PostgreSQL Fallback**

**API Endpoint:** `GET /result/{task_id}`

**Backend Logic (Smart Fallback):**

```python
# app/main.py - Lines 345-368

# Step 1: Try Redis first (fast, complete data)
result_json = redis_client.get(f"result:{task_id}")
if result_json:
    return PDFExtractionResult(**json.loads(result_json))
    # ✅ Returns: text, tables, images, metadata, page_count, time

# Step 2: Fallback to PostgreSQL if Redis expired (24h TTL)
document = db.query(Document).filter(Document.id == int(task_id)).first()
if document and document.result_text:
    return PDFExtractionResult(
        text=document.result_text,        # ← PostgreSQL
        page_count=document.page_count,   # ← PostgreSQL
        extraction_time=document.extraction_time_seconds,  # ← PostgreSQL
        tables=[],      # ❌ Not in PostgreSQL (too complex)
        images=[],      # ❌ Not in PostgreSQL (too large)
        metadata={}     # ❌ Not in PostgreSQL
    )
```

---

### **📝 Text Tab - Detailed Breakdown**

```
┌──────────────────────────────────────────────────────┐
│                   📝 Text Tab                        │
├──────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────┐   │
│ │ Lorem ipsum dolor sit amet...                │   │
│ │ [Full extracted text from LlamaParse]        │   │
│ │          ↑                                   │   │
│ │    🟢 Redis (recent tasks)                   │   │
│ │    🔵 PostgreSQL (old tasks, Redis expired) │   │
│ └──────────────────────────────────────────────┘   │
│ [💾 Download Text]                                  │
└──────────────────────────────────────────────────────┘
```

| Scenario | Data Source | Why |
|----------|-------------|-----|
| **Recent task (< 24h)** | 🟢 Redis `result:{task_id}` | Fast, full content |
| **Old task (> 24h)** | 🔵 PostgreSQL `documents.result_text` | Redis expired |

---

### **📊 Tables Tab - Detailed Breakdown**

```
┌──────────────────────────────────────────────────────┐
│                  📊 Tables Tab                       │
├──────────────────────────────────────────────────────┤
│ Table 1 (Page 2)                                     │
│ ┌─────────┬──────────┬──────────┐                   │
│ │ Name    │ Quantity │ Price    │  ← 🟢 Redis only │
│ ├─────────┼──────────┼──────────┤                   │
│ │ Item A  │ 100      │ $10.00   │                   │
│ └─────────┴──────────┴──────────┘                   │
└──────────────────────────────────────────────────────┘
```

| Scenario | Data Source | Content |
|----------|-------------|---------|
| **Recent task (< 24h)** | 🟢 Redis `result:{task_id}` | Full tables as JSON |
| **Old task (> 24h)** | ❌ **Not available** | Tables not stored in PostgreSQL |

**Why tables aren't in PostgreSQL:**
- Too complex to store as structured data
- Large JSON objects
- Redis TTL encourages timely downloads

---

### **🖼️ Images Tab - Detailed Breakdown**

```
┌──────────────────────────────────────────────────────┐
│                 🖼️ Images Tab                        │
├──────────────────────────────────────────────────────┤
│ Image 1      Image 2       Image 3                  │
│ Page 1       Page 2        Page 3   ← 🟢 Redis only│
│ Format: JPEG Format: PNG   Format: JPEG             │
│ Size: 800x600 Size: 1024x768 640x480                │
└──────────────────────────────────────────────────────┘
```

| Scenario | Data Source | Content |
|----------|-------------|---------|
| **Recent task (< 24h)** | 🟢 Redis `result:{task_id}` | Image metadata (page, format, size) |
| **Old task (> 24h)** | ❌ **Not available** | Images not stored in PostgreSQL |

**Why images aren't in PostgreSQL:**
- Only metadata stored, not actual images
- Large data size
- Redis TTL encourages timely access

---

### **📋 Metadata Tab - Detailed Breakdown**

```
┌──────────────────────────────────────────────────────┐
│               📋 Metadata Tab                        │
├──────────────────────────────────────────────────────┤
│ Document Info       │ Technical Info                 │
│ Title: Report       │ Producer: Adobe  ← 🟢 Redis only│
│ Author: John        │ Created: 2026-01-15            │
│ Subject: Finance    │ Modified: 2026-02-01           │
└──────────────────────────────────────────────────────┘
```

| Scenario | Data Source | Content |
|----------|-------------|---------|
| **Recent task (< 24h)** | 🟢 Redis `result:{task_id}` | Full PDF metadata |
| **Old task (> 24h)** | ❌ **Not available** | Metadata not stored in PostgreSQL |

---

## 📊 Complete Data Source Matrix

| UI Component | Primary Source | Fallback Source | TTL | Notes |
|--------------|----------------|-----------------|-----|-------|
| **All Tasks List** | 🟢 Redis | ❌ None | 24h | If Redis expires, task disappears from list |
| **Task Status** | 🟢 Redis | ❌ None | 24h | Status, progress, timestamps |
| **Extracted Text** | 🟢 Redis | 🔵 PostgreSQL | Forever (PG) | Text always available via PostgreSQL |
| **Tables** | 🟢 Redis | ❌ None | 24h | Download within 24h or lost |
| **Images** | 🟢 Redis | ❌ None | 24h | Metadata only, download within 24h |
| **Metadata** | 🟢 Redis | ❌ None | 24h | PDF properties, download within 24h |
| **Page Count** | 🟢 Redis | 🔵 PostgreSQL | Forever (PG) | Stored in PostgreSQL |
| **Extraction Time** | 🟢 Redis | 🔵 PostgreSQL | Forever (PG) | Stored in PostgreSQL |
| **PDF File** | 🔴 AWS S3 | ❌ None | Forever | Original PDF in S3 bucket |

---

## 🔄 Complete Data Flow Diagram

### **Upload → Processing → Display**

```
┌─────────────────────────────────────────────────────────────┐
│                    1. UPLOAD PHASE                          │
└─────────────────────────────────────────────────────────────┘
User uploads PDF
    ↓
FastAPI receives file
    ↓
┌───────────────────────────────────────────────────┐
│ 🔴 S3: Store PDF file                             │ ← Original PDF
│    Key: uploads/{uuid}.pdf                        │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│ 🔵 PostgreSQL: Create document record             │ ← Permanent
│    Fields: filename, s3_key, status=PENDING       │
│    Get document.id (e.g., 10)                     │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│ 🟢 Redis: Store task metadata (24h TTL)          │ ← Real-time
│    Key: task:10                                   │
│    Fields: status, progress, filename, timestamps │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│ 🟠 SQS: Queue processing job                      │ ← Job queue
│    Message: {task_id: 10, s3_key, filename}      │
└───────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   2. PROCESSING PHASE                       │
└─────────────────────────────────────────────────────────────┘
Worker polls SQS
    ↓
┌───────────────────────────────────────────────────┐
│ 🔴 S3: Download PDF                               │ ← Fetch file
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│ 🟢 Redis: Update progress (0% → 100%)            │ ← Live updates
│    Updates: task:10 → progress, status           │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│ 🔵 PostgreSQL: Update status=PROCESSING           │ ← Mark started
│    Update: documents.status, started_at           │
└───────────────────────────────────────────────────┘
    ↓
LlamaParse extracts content
    ↓
┌───────────────────────────────────────────────────┐
│ 🟢 Redis: Store full results (24h TTL)           │ ← Complete data
│    Key: result:10                                 │
│    Data: text, tables, images, metadata          │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│ 🔵 PostgreSQL: Store essential data               │ ← Permanent
│    Update: result_text, page_count,               │
│            extraction_time, status=COMPLETED      │
└───────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    3. DISPLAY PHASE                         │
└─────────────────────────────────────────────────────────────┘

UI Request: Show All Tasks
    ↓
┌───────────────────────────────────────────────────┐
│ 🟢 Redis: Fetch all tasks                        │ ← Source
│    Keys: all_tasks, task:*                       │
└───────────────────────────────────────────────────┘
    ↓
Display task list in Streamlit

UI Request: View Task Status
    ↓
┌───────────────────────────────────────────────────┐
│ 🟢 Redis: Fetch task metadata                    │ ← Source
│    Key: task:10                                   │
└───────────────────────────────────────────────────┘
    ↓
Display status, progress, timestamps

UI Request: View Results
    ↓
┌───────────────────────────────────────────────────┐
│ 🟢 Redis: Try to fetch results (fast)            │ ← Primary
│    Key: result:10                                 │
└───────────────────────────────────────────────────┘
    ↓
If Redis data exists:
    → Display: text, tables, images, metadata, page_count
    
If Redis expired (404):
    ↓
┌───────────────────────────────────────────────────┐
│ 🔵 PostgreSQL: Fetch from database                │ ← Fallback
│    Query: SELECT result_text, page_count          │
│           FROM documents WHERE id = 10            │
└───────────────────────────────────────────────────┘
    ↓
Display: text, page_count, extraction_time
(⚠️ No tables, images, metadata - not stored in PG)
```

---

## ⏰ Time-Based Data Availability

### **Within 24 Hours (Recent Tasks)**

```
✅ Available from Redis (fast):
- Task list
- Task status & progress
- Full extracted text
- Tables (as DataFrames)
- Images (metadata)
- PDF metadata
- Page count
- Extraction time

✅ Available from PostgreSQL (permanent):
- Document record
- Extracted text
- Page count
- Extraction time
- Status history

✅ Available from S3:
- Original PDF file
```

---

### **After 24 Hours (Old Tasks)**

```
❌ NOT available (Redis expired):
- Task in "All Tasks" list
- Real-time status
- Tables
- Images
- PDF metadata

✅ Still available from PostgreSQL:
- Document record
- Extracted text
- Page count
- Extraction time
- Status (final)

✅ Still available from S3:
- Original PDF file

💡 Workaround: Query PostgreSQL directly:
   GET /documents/{document_id}
```

---

## 🎯 Quick Reference: Where Is My Data?

| Question | Answer |
|----------|--------|
| **Where is the task list?** | 🟢 Redis `all_tasks` |
| **Where is task status?** | 🟢 Redis `task:{task_id}` |
| **Where is extracted text?** | 🟢 Redis (recent) OR 🔵 PostgreSQL (always) |
| **Where are tables?** | 🟢 Redis only (24h) |
| **Where are images?** | 🟢 Redis only (24h) |
| **Where is PDF metadata?** | 🟢 Redis only (24h) |
| **Where is the original PDF?** | 🔴 AWS S3 (forever) |
| **Where is the job queue?** | 🟠 AWS SQS (not displayed) |

---

## 💡 Best Practices

1. **Download important data within 24 hours** - Tables and images expire from Redis
2. **Text is always safe** - Stored permanently in PostgreSQL
3. **Use PostgreSQL endpoints** for historical queries beyond 24h
4. **S3 files never expire** - Original PDFs available forever

---

## 🔧 Testing Data Sources

### **Test Redis Data:**
```bash
redis-cli
> GET result:10
> HGETALL task:10
> LRANGE all_tasks 0 -1
```

### **Test PostgreSQL Data:**
```sql
SELECT id, filename, status, result_text, page_count 
FROM documents 
WHERE id = 10;
```

### **Test S3 Data:**
```bash
aws s3 ls s3://your-bucket/uploads/
```

---

**Summary:** Your UI primarily uses **Redis for speed**, with **PostgreSQL as permanent backup** for essential data (text, metadata), and **S3 for file storage**. 🚀
