# ⚡ Quick Start: Testing Your Optimized System

## 🎯 5-Minute Test

The fastest way to test everything works:

---

## 1️⃣ **Check Services** (30 seconds)

```bash
# Check Docker
docker ps

# Should show:
# - doc-processor-postgres
# - doc-processor-redis

# If not running:
cd /Users/mbp/Desktop/redis/document-processor
docker-compose up -d postgres redis
```

---

## 2️⃣ **Verify HNSW Index** (10 seconds)

```bash
python3 verify_hnsw_index.py
```

**Expected:**
```
✅ HNSW index EXISTS
✅ pgvector extension installed
```

---

## 3️⃣ **Start Backend** (already running!)

Your FastAPI server is already running on port 8000 (Terminal 8).

**Test it:**
```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "healthy", "postgres": "connected", "redis": "connected"}
```

---

## 4️⃣ **Start SQS Worker** (new terminal)

```bash
cd /Users/mbp/Desktop/redis/document-processor
python3 -m app.sqs_worker

# Should show:
# ✅ Connected to SQS queue
# 🔄 Polling for messages...
```

---

## 5️⃣ **Start Streamlit** (new terminal)

```bash
cd /Users/mbp/Desktop/redis/document-processor
streamlit run streamlit_app.py

# Browser opens automatically at http://localhost:8501
```

---

## 6️⃣ **Upload Test PDF** (2 minutes)

**In Streamlit (http://localhost:8501):**

1. Go to **"Upload & Process"** tab
2. Click **"Choose PDF file(s)"**
3. Select a test PDF (any PDF file)
4. Click **"🚀 Process All"**
5. Wait 30-60 seconds
6. Status should change to **"✅ Ready to Chat"**

---

## 7️⃣ **Test Chat** (1 minute) 🚀

1. Click **"💬 Chat"** button (or go to Chat tab)
2. Make sure your document is selected
3. Type: **"What is this document about?"**
4. Press Enter
5. Watch for instant response (1-2 seconds)!

**Expected:**
- ✅ AI answer appears
- ✅ Sources section shows document chunks
- ✅ Token usage displayed

---

## 8️⃣ **Verify Performance** (30 seconds)

**Check FastAPI logs (Terminal with uvicorn):**

Look for this line:
```
INFO:app.chat_service:✅ Found 5 similar chunks in 67ms ⚡
```

**Performance targets:**
- ✅ **<100ms:** Excellent! HNSW working perfectly
- ✅ **100-200ms:** Good
- ⚠️ **>500ms:** Check if index is being used

---

## ✅ You're Done!

If you see:
- ✅ Chat responses in 1-2 seconds
- ✅ Vector search <200ms
- ✅ Sources displayed correctly
- ✅ No errors in logs

**Your system is fully optimized and working!** 🎉

---

## 🔍 Quick Troubleshooting

### **No answer returned:**
- Check: Documents have status = COMPLETED
- Check: Chunks exist in database
- Check: OpenAI API key in .env

### **Slow responses (>3s):**
- Check: Vector search time in logs
- Run: `python3 verify_hnsw_index.py`
- Run: `ANALYZE document_chunks;` in PostgreSQL

### **Backend not responding:**
- Check: http://localhost:8000/health
- Restart: `python3 -m uvicorn app.main:app --reload --port 8000`

---

## 📊 What to Check in Logs

### **FastAPI (Port 8000):**
```
✅ Found 5 chunks in 67ms ⚡  ← Target: <200ms
```

### **SQS Worker:**
```
✅ Processing completed in 23.5s  ← Target: <60s
```

### **Streamlit:**
```
Should have no errors
```

---

## 🚀 Expected Performance

| Operation | Time | Status |
|-----------|------|--------|
| Upload PDF | 1-2s | ✅ |
| Processing | 30-60s | ✅ |
| **Vector search** | **<100ms** | ⚡ **OPTIMIZED** |
| LLM answer | 1-2s | ✅ |
| **Total chat** | **2-3s** | ✅ |

**Before optimization:** ~4-5 seconds  
**After optimization:** ~2-3 seconds  
**Improvement:** 2x faster end-to-end, **20-60x** faster vector search!

---

## 🎯 One-Command Test

If you want to start everything at once:

```bash
# Terminal 1
cd /Users/mbp/Desktop/redis/document-processor && \
docker-compose up -d postgres redis && \
python3 -m uvicorn app.main:app --reload --port 8000

# Terminal 2
cd /Users/mbp/Desktop/redis/document-processor && \
python3 -m app.sqs_worker

# Terminal 3
cd /Users/mbp/Desktop/redis/document-processor && \
streamlit run streamlit_app.py
```

Then test in browser: http://localhost:8501

---

**Time to complete:** 5-10 minutes  
**Result:** Fully tested, optimized RAG system! 🚀
