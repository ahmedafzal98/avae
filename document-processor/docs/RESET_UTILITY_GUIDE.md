# 🚨 Environment Reset Utility Guide

## Overview

`reset_env.py` is a **DESTRUCTIVE** utility script that completely wipes all test data across your entire stack so you can start fresh for testing.

⚠️ **WARNING: This is IRREVERSIBLE! Use with extreme caution!**

---

## 🎯 What This Script Does

The script safely resets 4 services in your stack:

### 1. **PostgreSQL** 🗄️
- Truncates `documents` table (CASCADE to `document_chunks`)
- Optionally truncates `users` table
- Keeps schema intact (tables, indexes, etc.)
- Shows count of records deleted

### 2. **Redis** 🔴
- Deletes keys matching patterns:
  - `task:*` - Task metadata
  - `result:*` - Processing results
  - `progress:*` - Progress tracking
  - `rate_limit:*` - Rate limiting data

### 3. **AWS S3** ☁️
- Deletes ALL objects/PDFs in your uploads bucket
- Lists files before deletion
- Batch deletion (1000 objects at a time)

### 4. **AWS SQS** 📨
- Purges all messages from your queue
- Shows visible + in-flight message counts
- Clears the queue completely

---

## 🚀 Usage

### **Interactive Mode (Recommended)**

```bash
cd /Users/mbp/Desktop/redis/document-processor
python3 reset_env.py
```

**You'll be prompted:**
1. "Are you ABSOLUTELY SURE?" - Type `yes`
2. "Type 'DELETE ALL DATA'" - Type exactly `DELETE ALL DATA`
3. "Also delete ALL USERS?" - Type `yes` or `no`

---

### **Dry Run Mode (Safe Testing)**

See what would be deleted WITHOUT actually deleting:

```bash
python3 reset_env.py --dry-run
```

**Output shows:**
- How many documents would be deleted
- How many Redis keys would be deleted
- How many S3 objects would be deleted
- How many SQS messages would be purged

---

### **Force Mode (Skip Confirmations)**

⚠️ **DANGEROUS - Use only in scripts/CI:**

```bash
python3 reset_env.py --force
```

---

### **Selective Reset**

Reset only specific services:

```bash
# Reset only PostgreSQL and Redis (skip AWS)
python3 reset_env.py --skip-s3 --skip-sqs

# Reset only S3
python3 reset_env.py --skip-postgres --skip-redis --skip-sqs

# Reset only PostgreSQL
python3 reset_env.py --skip-redis --skip-s3 --skip-sqs
```

---

## 📊 Example Output

### Interactive Mode

```
🔍 Checking environment...
   📍 Environment: 127.0.0.1:5433/document_processor

============================================================
🚨 DANGER ZONE: COMPLETE ENVIRONMENT RESET 🚨
============================================================

This will DELETE ALL DATA from:
  • PostgreSQL: documents, document_chunks, users tables
  • Redis: all task:*, result:*, progress:* keys
  • AWS S3: all uploaded PDFs
  • AWS SQS: all queued messages

⚠️  THIS OPERATION IS IRREVERSIBLE!
⚠️  ALL YOUR DATA WILL BE PERMANENTLY LOST!
============================================================

Are you ABSOLUTELY SURE you want to continue? (yes/no): yes

⚠️  FINAL WARNING: This cannot be undone!
Type 'DELETE ALL DATA' to confirm: DELETE ALL DATA

Also delete ALL USERS? This will reset authentication (yes/no): no

✅ Confirmation received. Starting reset...

============================================================
🗄️  POSTGRESQL RESET
============================================================
📊 Counting records before deletion...
   📄 Documents: 15
   📦 Document chunks: 1,234

🗑️  Truncating tables...
   Truncating documents (CASCADE to chunks)...
   ✅ Documents and chunks truncated

✅ PostgreSQL reset complete!
   📄 Documents deleted: 15 (remaining: 0)
   📦 Chunks deleted: 1,234 (remaining: 0)

============================================================
🔴 REDIS RESET
============================================================

🔍 Scanning for keys matching: task:*
   Found 10 keys
   ✅ Deleted 10 keys

🔍 Scanning for keys matching: result:*
   Found 8 keys
   ✅ Deleted 8 keys

🔍 Scanning for keys matching: progress:*
   Found 5 keys
   ✅ Deleted 5 keys

🔍 Scanning for keys matching: rate_limit:*
   No keys found

✅ Redis reset complete! Total keys deleted: 23

============================================================
☁️  AWS S3 RESET
============================================================
🪣 Bucket: my-document-uploads-2026
📋 Listing objects...
   Found 15 objects

📄 Sample of objects to delete:
   - uploads/abc123.pdf
   - uploads/def456.pdf
   - uploads/ghi789.pdf
   - uploads/jkl012.pdf
   - uploads/mno345.pdf
   ... and 10 more

🗑️  Deleting 15 objects...
   ✅ Batch 1: Deleted 15 objects

✅ S3 reset complete! Objects deleted: 15

============================================================
📨 AWS SQS RESET
============================================================
📬 Queue URL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
📊 Checking queue status...
   📨 Visible messages: 3
   👻 In-flight messages: 1
   📊 Total messages: 4

🗑️  Purging 4 messages...
✅ SQS queue purged successfully!
   Note: Messages may take up to 60 seconds to be fully cleared

============================================================
📊 RESET SUMMARY
============================================================

🗄️  PostgreSQL:
   📄 Documents deleted: 15
   📦 Chunks deleted: 1,234

🔴 Redis:
   🔑 Keys deleted: 23

☁️  AWS S3:
   📁 Objects deleted: 15

📨 AWS SQS:
   📬 Messages purged: 4

============================================================
✅ RESET COMPLETE - All test data wiped clean!
============================================================

🎉 Environment reset completed successfully!
```

---

### Dry Run Mode

```bash
$ python3 reset_env.py --dry-run

🔍 DRY RUN MODE - No data will actually be deleted

============================================================
🗄️  POSTGRESQL RESET
============================================================
📊 Counting records before deletion...
   📄 Documents: 15
   📦 Document chunks: 1,234

🔍 [DRY RUN] Would truncate tables

...

============================================================
🔍 DRY RUN COMPLETE - No data was actually deleted
============================================================
```

---

## 🛡️ Safety Features

### 1. **Multi-Stage Confirmation**
- First prompt: "Are you ABSOLUTELY SURE?" → requires `yes`
- Second prompt: Type exact text `DELETE ALL DATA`
- Third prompt: Confirm user deletion → `yes` or `no`

### 2. **Production Detection**
- Checks if hostname contains `prod` or `production`
- **Automatically aborts** if production detected
- No override available (by design)

### 3. **Dry Run Mode**
- Shows exactly what would be deleted
- No actual deletion happens
- Perfect for testing or verification

### 4. **Detailed Logging**
- Console output (STDOUT)
- Log file: `reset_env_YYYYMMDD_HHMMSS.log`
- All operations logged with timestamps

### 5. **Error Handling**
- Each service reset is independent
- Failure in one service doesn't stop others
- Exit code 1 if any operation fails

---

## 📋 When to Use This

### **Good Use Cases:**

✅ **After bulk testing** - Clear test data between test cycles  
✅ **Development reset** - Start fresh during development  
✅ **Demo preparation** - Clean slate before demos  
✅ **Schema changes** - After modifying database schema  
✅ **Testing migrations** - Clean state for testing migrations

### **Bad Use Cases:**

❌ **Production environments** - NEVER use in production!  
❌ **Partial cleanup** - Use SQL queries for selective deletion  
❌ **Regular operations** - This is for complete resets only  
❌ **Live systems** - Stop all services before running

---

## 🔄 Recommended Workflow

### **Complete Fresh Start:**

```bash
# 1. Stop all services
pkill -f uvicorn          # Stop FastAPI
pkill -f sqs_worker       # Stop worker
pkill -f streamlit        # Stop Streamlit

# 2. Run reset (dry-run first!)
python3 reset_env.py --dry-run

# 3. Verify dry-run looks good, then reset for real
python3 reset_env.py

# 4. Verify everything is clean
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT 
    (SELECT COUNT(*) FROM documents) as docs,
    (SELECT COUNT(*) FROM document_chunks) as chunks,
    (SELECT COUNT(*) FROM users) as users;
"

# Expected output:
#  docs | chunks | users
# ------+--------+-------
#     0 |      0 |     X  (X = 0 if you deleted users, >0 if you kept them)

# 5. Start services and test
python3 -m uvicorn app.main:app --reload --port 8000  # Terminal 1
python3 -m app.sqs_worker                             # Terminal 2
streamlit run streamlit_app.py                        # Terminal 3

# 6. Upload a fresh test document and verify everything works
```

---

## 🧪 Testing the Script

### **Test in Dry Run First:**

```bash
# See what would happen without risk
python3 reset_env.py --dry-run
```

### **Test Individual Services:**

```bash
# Test PostgreSQL reset only
python3 reset_env.py --dry-run --skip-redis --skip-s3 --skip-sqs

# Test Redis reset only
python3 reset_env.py --dry-run --skip-postgres --skip-s3 --skip-sqs
```

---

## 🐛 Troubleshooting

### **Error: "Failed to load configuration"**

**Cause:** Missing `.env` file or invalid settings

**Fix:**
```bash
# Check .env exists
ls -la .env

# Verify required variables
cat .env | grep -E '(POSTGRES|REDIS|AWS)'
```

---

### **Error: "could not connect to server"**

**Cause:** PostgreSQL not running

**Fix:**
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Verify it's running
docker ps | grep postgres
```

---

### **Error: "Connection refused (Redis)"**

**Cause:** Redis not running

**Fix:**
```bash
# Start Redis
docker-compose up -d redis

# Verify it's running
docker ps | grep redis
```

---

### **Error: "The specified queue does not exist"**

**Cause:** SQS queue URL is incorrect

**Fix:**
```bash
# Check queue URL in .env
cat .env | grep SQS_QUEUE_URL

# Verify queue exists in AWS Console
```

---

### **Error: "Access Denied (S3)"**

**Cause:** AWS credentials lack S3 permissions

**Fix:**
- Verify AWS credentials in `.env`
- Check IAM permissions include `s3:ListBucket`, `s3:DeleteObject`
- Test with: `aws s3 ls s3://your-bucket-name`

---

## 📝 Log Files

Each run creates a log file:

```
reset_env_20260220_143022.log
reset_env_20260220_144505.log
```

**Log location:** Same directory as script  
**Format:** `reset_env_YYYYMMDD_HHMMSS.log`

**Useful for:**
- Auditing what was deleted
- Debugging failures
- Tracking reset history

---

## 🔐 Security Notes

### **What's Safe:**

✅ Runs in **development/testing** environments only  
✅ Aborts if "prod" or "production" detected  
✅ Requires multiple confirmations  
✅ Dry-run mode for testing  
✅ Detailed logging of all operations

### **What's NOT Safe:**

❌ Using `--force` flag without understanding consequences  
❌ Running on production credentials  
❌ Running while services are processing data  
❌ Interrupting mid-reset (Ctrl+C)

---

## 💡 Pro Tips

1. **Always dry-run first:**
   ```bash
   python3 reset_env.py --dry-run
   ```

2. **Stop services before reset:**
   - Prevents orphaned tasks
   - Avoids database locks
   - Clean reset state

3. **Keep one test user:**
   - Answer "no" to "Also delete ALL USERS?"
   - Keeps your test user credentials
   - Only wipes documents and chunks

4. **Check logs after reset:**
   ```bash
   tail -f reset_env_*.log
   ```

5. **Verify reset worked:**
   ```bash
   # Check PostgreSQL
   psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
     SELECT 
       (SELECT COUNT(*) FROM documents) as docs,
       (SELECT COUNT(*) FROM document_chunks) as chunks;
   "
   
   # Check Redis
   redis-cli KEYS "task:*" | wc -l
   
   # Check S3
   aws s3 ls s3://your-bucket-name --recursive | wc -l
   ```

---

## 🎬 Common Scenarios

### **Scenario 1: Fresh Start for Testing**

```bash
# Stop services
pkill -f uvicorn && pkill -f sqs_worker && pkill -f streamlit

# Reset everything (keep users)
python3 reset_env.py
# Answer: yes → DELETE ALL DATA → no

# Restart and test
python3 -m uvicorn app.main:app --reload --port 8000
```

---

### **Scenario 2: Complete Wipe (Including Users)**

```bash
python3 reset_env.py
# Answer: yes → DELETE ALL DATA → yes

# This removes:
# - All users
# - All documents
# - All chunks
# - All Redis data
# - All S3 files
# - All SQS messages
```

---

### **Scenario 3: Reset Before Running HNSW Migration**

```bash
# Reset to clean state
python3 reset_env.py

# Upload fresh test data
# (via Streamlit or API)

# Run HNSW migration
python3 migrations/run_migration.py

# Test with clean, indexed data
```

---

### **Scenario 4: CI/CD Pipeline Reset**

```bash
# In your CI script
python3 reset_env.py --force --dry-run  # Verify first
python3 reset_env.py --force            # Then execute

# Run integration tests
pytest tests/integration/
```

---

## 🧪 Testing the Reset Script

### **Test 1: Dry Run**

```bash
# Should show counts but not delete anything
python3 reset_env.py --dry-run

# Verify nothing was deleted
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT COUNT(*) FROM documents;
"
# Should show same count as before
```

---

### **Test 2: Reset with Data**

```bash
# 1. Upload test documents first
# (via Streamlit - upload 2-3 PDFs)

# 2. Verify data exists
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT COUNT(*) FROM documents;
"
# Should show > 0

# 3. Run reset
python3 reset_env.py

# 4. Verify data is gone
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT COUNT(*) FROM documents;
"
# Should show 0
```

---

### **Test 3: Partial Reset**

```bash
# Reset only PostgreSQL and Redis, keep S3/SQS
python3 reset_env.py --skip-s3 --skip-sqs

# Verify S3 still has files
aws s3 ls s3://your-bucket-name
```

---

## 📊 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - all resets completed |
| 1 | Failure - one or more resets failed |
| 1 | User cancelled (Ctrl+C or declined confirmation) |

---

## 🔧 Advanced Options

### **Customize Redis Patterns**

Edit the script to add custom patterns:

```python
# In reset_redis() method
patterns = ['task:*', 'result:*', 'progress:*', 'your_custom_pattern:*']
```

---

### **Keep Specific Users**

The script currently keeps/deletes ALL users. To keep specific users, edit:

```python
# In reset_postgresql() method, instead of TRUNCATE:
DELETE FROM documents WHERE user_id NOT IN (1, 2);  # Keep users 1 and 2
```

---

### **Add More Services**

To reset additional services, add new methods:

```python
def reset_elasticsearch(self) -> bool:
    """Reset Elasticsearch indices"""
    # Your implementation
    pass
```

---

## 📋 Pre-Reset Checklist

Before running the reset:

- [ ] All services stopped (FastAPI, SQS worker, Streamlit)
- [ ] You have run `--dry-run` and verified output
- [ ] You are in **DEVELOPMENT** environment (not production!)
- [ ] You have a backup (if needed)
- [ ] You understand this is **IRREVERSIBLE**
- [ ] You are prepared to re-upload test data

---

## 🎯 After Reset

Once reset is complete:

1. **Verify clean state:**
   ```bash
   # PostgreSQL should be empty
   psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
     SELECT 
       (SELECT COUNT(*) FROM documents) as docs,
       (SELECT COUNT(*) FROM document_chunks) as chunks;
   "
   # Expected: docs = 0, chunks = 0
   
   # Redis should be clean
   redis-cli KEYS "task:*" | wc -l
   # Expected: 0
   
   # S3 should be empty
   aws s3 ls s3://your-bucket-name --recursive | wc -l
   # Expected: 0
   ```

2. **Start services:**
   ```bash
   python3 -m uvicorn app.main:app --reload --port 8000  # Terminal 1
   python3 -m app.sqs_worker                             # Terminal 2
   streamlit run streamlit_app.py                        # Terminal 3
   ```

3. **Upload fresh test data:**
   - Open http://localhost:8501
   - Upload 1-2 test PDFs
   - Verify processing works end-to-end

4. **Test RAG chat:**
   - Wait for documents to be "Ready to Chat"
   - Switch to Chat tab
   - Ask a question
   - Verify responses work

---

## ⚠️ Important Notes

### **CASCADE Behavior:**

When you truncate `documents`, PostgreSQL automatically:
- Truncates `document_chunks` (due to CASCADE)
- Maintains all indexes (including HNSW!)
- Keeps table schemas intact
- Resets auto-increment sequences

### **Users Table:**

- By default, **users are kept** (preserves authentication)
- You can optionally delete users when prompted
- If you delete users, you'll need to recreate them

### **S3 Deletion:**

- Deletes objects, not the bucket itself
- Bucket remains for new uploads
- Deletion is permanent (no versioning in this setup)

### **SQS Purge:**

- Messages are purged but queue remains
- Takes up to 60 seconds to fully clear
- New messages can be sent immediately

---

## 🚫 What This Script Does NOT Do

❌ **Does NOT:**
- Drop tables or schemas
- Delete the database itself
- Remove Docker containers
- Delete your `.env` file
- Remove code or migrations
- Delete the S3 bucket (only objects)
- Delete the SQS queue (only messages)
- Modify any configuration files

✅ **ONLY:**
- Removes **DATA** from existing structures
- Keeps all infrastructure intact
- Preserves schemas, indexes, queues, buckets

---

## 📞 Need Help?

If something goes wrong:

1. **Check the log file:**
   ```bash
   cat reset_env_*.log | grep ERROR
   ```

2. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

3. **Test connections manually:**
   ```bash
   # PostgreSQL
   psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "SELECT 1;"
   
   # Redis
   redis-cli ping
   
   # AWS
   aws s3 ls
   aws sqs list-queues
   ```

---

## 🎉 Summary

This utility provides a **safe, controlled way** to completely reset your development environment. 

**Key features:**
- ✅ Multi-stage safety confirmations
- ✅ Production detection and abort
- ✅ Dry-run mode for testing
- ✅ Detailed logging
- ✅ Selective service reset
- ✅ Comprehensive error handling

**Use it wisely, and always dry-run first!** 🚀

---

**Created:** 2026-02-20  
**Script:** `reset_env.py`  
**Status:** ✅ Ready to use
