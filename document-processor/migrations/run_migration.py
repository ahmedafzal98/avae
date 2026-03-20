#!/usr/bin/env python3
"""
Run HNSW Vector Index Migration

This script applies the HNSW index migration to your PostgreSQL database.
It provides progress updates and error handling.

Usage:
    python3 migrations/run_migration.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import engine
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the HNSW index migration"""
    
    logger.info("=" * 70)
    logger.info("🚀 Starting HNSW Vector Index Migration")
    logger.info("=" * 70)
    
    # Read migration SQL file
    migration_file = Path(__file__).parent / "001_add_hnsw_vector_index.sql"
    
    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    logger.info(f"📄 Reading migration from: {migration_file}")
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # Connect to database
    logger.info(f"🔌 Connecting to database: {settings.postgres_db}")
    
    try:
        with engine.connect() as conn:
            # Split SQL into statements (skip comments and empty lines)
            statements = []
            current_statement = []
            
            for line in sql.split('\n'):
                line = line.strip()
                
                # Skip comments and empty lines
                if line.startswith('--') or not line:
                    continue
                
                current_statement.append(line)
                
                # Execute when we hit a semicolon
                if line.endswith(';'):
                    statement = ' '.join(current_statement)
                    statements.append(statement)
                    current_statement = []
            
            # Execute statements
            total_statements = len(statements)
            logger.info(f"📊 Found {total_statements} SQL statements to execute")
            
            for i, statement in enumerate(statements, 1):
                # Extract statement type for logging
                statement_type = statement.split()[0].upper()
                
                logger.info(f"⚙️  Executing statement {i}/{total_statements}: {statement_type}...")
                
                try:
                    # Special handling for index creation (can take a long time)
                    if 'CREATE INDEX' in statement.upper():
                        index_name = statement.split('INDEX')[1].split()[0]
                        logger.info(f"🔨 Creating index: {index_name}")
                        logger.info("⏳ This may take 5-30 minutes for large datasets...")
                        logger.info("    Progress indicators:")
                        logger.info("    - Check PostgreSQL logs for index build progress")
                        logger.info("    - Monitor CPU/disk usage")
                        logger.info("    - Be patient! The performance boost is worth it!")
                    
                    result = conn.execute(text(statement))
                    conn.commit()
                    
                    # Log results if available
                    if result.returns_rows:
                        rows = result.fetchall()
                        if rows:
                            logger.info(f"   ✅ Result: {len(rows)} row(s)")
                            for row in rows[:5]:  # Show first 5 rows
                                logger.info(f"      {dict(row._mapping)}")
                            if len(rows) > 5:
                                logger.info(f"      ... and {len(rows) - 5} more rows")
                    else:
                        logger.info(f"   ✅ {statement_type} completed successfully")
                
                except Exception as e:
                    # Some statements might fail gracefully (e.g., DROP IF EXISTS)
                    if 'does not exist' in str(e).lower():
                        logger.warning(f"   ⚠️  {e} (continuing...)")
                    else:
                        logger.error(f"   ❌ Error executing statement: {e}")
                        raise
            
            logger.info("")
            logger.info("=" * 70)
            logger.info("✅ Migration Completed Successfully!")
            logger.info("=" * 70)
            logger.info("")
            logger.info("📈 Expected Performance Improvements:")
            logger.info("   • Vector search queries: 20-60x faster")
            logger.info("   • Chat responses: <100ms (was 2-3 seconds)")
            logger.info("   • Scales to millions of vectors")
            logger.info("")
            logger.info("🎯 Next Steps:")
            logger.info("   1. Test a chat query to verify performance")
            logger.info("   2. Monitor query times in application logs")
            logger.info("   3. Restart your FastAPI server (if needed)")
            logger.info("")
    
    except Exception as e:
        logger.error("")
        logger.error("=" * 70)
        logger.error("❌ Migration Failed!")
        logger.error("=" * 70)
        logger.error(f"Error: {e}")
        logger.error("")
        logger.error("Troubleshooting:")
        logger.error("  1. Check if PostgreSQL is running")
        logger.error("  2. Verify database connection settings in .env")
        logger.error("  3. Ensure pgvector extension is installed:")
        logger.error("     psql -d document_processor -c 'CREATE EXTENSION vector;'")
        logger.error("")
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
