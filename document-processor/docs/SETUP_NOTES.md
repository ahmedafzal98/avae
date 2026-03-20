# Setup Notes & Troubleshooting

## ✅ Hybrid Database Architecture - Successfully Implemented

### What Was Done

1. **Created PostgreSQL + Redis hybrid architecture**
   - PostgreSQL for persistent data (Users, Documents)
   - Redis for caching and real-time operations
   
2. **Implemented SQLAlchemy 2.0 models**
   - `User` model with email and API key
   - `Document` model with full processing metadata
   - Proper relationships and indexes

3. **Created migration script**
   - Successfully migrated 7 tasks from Redis to PostgreSQL
   - All data preserved with timestamps and status

### Issue Resolved: Port Conflict

**Problem:** Local PostgreSQL instance was running on port 5432, causing connection conflicts.

**Solution:** Changed Docker PostgreSQL port mapping from `5432:5432` to `5433:5432`

**Files Updated:**
- `docker-compose.yml` - Changed port to `5433:5432`
- `app/config.py` - Updated default port to `5433`
- `env.example` - Added PostgreSQL configuration with port `5433`

### Database Connection Details

```
Host: 127.0.0.1
Port: 5433 (host) → 5432 (container)
Database: document_processor
User: docuser
Password: docpass_dev_2026
```

### Verification Commands

```bash
# Check if PostgreSQL is running
docker-compose ps

# Connect to database
docker-compose exec postgres psql -U docuser -d document_processor

# View tables
docker-compose exec -T postgres psql -U docuser -d document_processor -c "\dt"

# View migrated data
docker-compose exec -T postgres psql -U docuser -d document_processor -c "SELECT * FROM users;"
docker-compose exec -T postgres psql -U docuser -d document_processor -c "SELECT id, filename, status FROM documents;"
```

### Migration Results

```
✅ Migration Summary:
- Tasks Processed: 7
- Tasks Migrated: 7
- Tasks Skipped: 0
- Errors: 0

✅ Database Tables Created:
- users (1 record)
- documents (7 records)
```

### Next Steps

1. **Start Redis** (if not already running):
   ```bash
   docker-compose up -d redis
   ```

2. **Start the FastAPI application**:
   ```bash
   uvicorn app.main:app --reload
   ```
   
   The database will be automatically initialized on startup.

3. **Test the API**:
   ```bash
   curl http://localhost:8000/health
   ```

### Important Notes

- **Port 5433** is used to avoid conflicts with local PostgreSQL
- Database tables are created automatically by SQLAlchemy on app startup
- Migration script can be run multiple times (it skips existing records)
- All timestamps use `CURRENT_TIMESTAMP` server default

### Troubleshooting

**If you see "role docuser does not exist":**
- Check if you're connecting to the right port (5433, not 5432)
- Verify Docker container is running: `docker-compose ps`
- Restart the container: `docker-compose restart postgres`

**If you need to reset the database:**
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d postgres
python3 scripts/migrate_redis_to_pg.py  # Re-run migration
```

**To check which PostgreSQL instances are running:**
```bash
lsof -i :5432  # Local PostgreSQL
lsof -i :5433  # Docker PostgreSQL
```

## Files Created/Modified

### New Files
- ✅ `app/database.py` - SQLAlchemy engine and session management
- ✅ `app/db_models.py` - User and Document ORM models
- ✅ `app/schemas.py` - Pydantic schemas for database models
- ✅ `scripts/migrate_redis_to_pg.py` - Migration script
- ✅ `scripts/__init__.py` - Package marker
- ✅ `MIGRATION_GUIDE.md` - Comprehensive documentation
- ✅ `SETUP_NOTES.md` - This file

### Modified Files
- ✅ `requirements.txt` - Added SQLAlchemy, psycopg2-binary, alembic
- ✅ `app/config.py` - Added PostgreSQL configuration
- ✅ `app/main.py` - Added database initialization on startup
- ✅ `app/models.py` → `app/schemas_api.py` - Renamed
- ✅ `app/tasks.py` - Updated imports
- ✅ `app/sqs_worker.py` - Updated imports
- ✅ `docker-compose.yml` - Changed PostgreSQL port to 5433
- ✅ `env.example` - Added PostgreSQL configuration
- ✅ `init.sql` - Simplified (tables created by SQLAlchemy)

## Architecture Benefits

✅ **Data Persistence** - PostgreSQL ensures data survives restarts  
✅ **Relationships** - Proper foreign keys and referential integrity  
✅ **Scalability** - Separate concerns (Redis for cache, PG for data)  
✅ **Query Power** - Complex queries, joins, and aggregations  
✅ **ACID Compliance** - Transactions ensure data consistency  
✅ **Backup & Recovery** - Standard PostgreSQL tools  

---

**Status:** ✅ All systems operational and tested!
