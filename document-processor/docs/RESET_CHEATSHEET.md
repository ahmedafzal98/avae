# 🚨 Reset Utility - Quick Reference

## 📋 Quick Commands

```bash
# Safe exploration - see what would be deleted
python3 reset_env.py --dry-run

# Interactive reset (recommended)
python3 reset_env.py

# Force reset (skip prompts - DANGEROUS!)
python3 reset_env.py --force

# Reset only specific services
python3 reset_env.py --skip-s3 --skip-sqs  # Keep AWS, reset local only
```

---

## 🎯 Common Workflows

### **Fresh Start for Testing**

```bash
# 1. Stop all services
pkill -f uvicorn && pkill -f sqs_worker && pkill -f streamlit

# 2. Reset (keep users)
python3 reset_env.py
# → yes → DELETE ALL DATA → no

# 3. Restart services
python3 -m uvicorn app.main:app --reload --port 8000 &
python3 -m app.sqs_worker &
streamlit run streamlit_app.py
```

---

### **Complete Wipe (Including Users)**

```bash
python3 reset_env.py
# → yes → DELETE ALL DATA → yes
```

---

### **Reset Before HNSW Migration**

```bash
# 1. Reset to clean state
python3 reset_env.py

# 2. Upload fresh test data (via Streamlit)

# 3. Run HNSW migration
python3 migrations/run_migration.py
```

---

## ✅ Verify Reset Worked

```bash
# Check PostgreSQL
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "
  SELECT 
    (SELECT COUNT(*) FROM documents) as docs,
    (SELECT COUNT(*) FROM document_chunks) as chunks,
    (SELECT COUNT(*) FROM users) as users;
"
# Expected: docs=0, chunks=0

# Check Redis
redis-cli KEYS "task:*" | wc -l
# Expected: 0

# Check S3
aws s3 ls s3://your-bucket-name --recursive | wc -l
# Expected: 0
```

---

## 🛡️ Safety Features

- ✅ Multi-stage confirmation (3 prompts)
- ✅ Production environment detection
- ✅ Dry-run mode
- ✅ Detailed logging to file
- ✅ Per-service error handling

---

## 📊 What Gets Deleted

| Service | What's Deleted | What's Kept |
|---------|----------------|-------------|
| **PostgreSQL** | All rows in documents, document_chunks, (optionally users) | Tables, indexes, schema |
| **Redis** | task:\*, result:\*, progress:\*, rate_limit:\* keys | Redis server, other keys |
| **S3** | All uploaded PDF objects | Bucket itself |
| **SQS** | All queued messages | Queue itself |

---

## ⚠️ Important Notes

- **Stop services first** to avoid orphaned data
- **Always dry-run first** to verify what will be deleted
- **NOT for production** - development/testing only
- **Logs saved** to `reset_env_YYYYMMDD_HHMMSS.log`
- **IRREVERSIBLE** - cannot undo!

---

## 🚀 Quick Start

```bash
# First time? Test it safely:
python3 reset_env.py --dry-run

# Happy with the output? Run for real:
python3 reset_env.py
```

---

For detailed documentation, see: **RESET_UTILITY_GUIDE.md**
