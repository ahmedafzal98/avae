"""Database utility functions for index management and verification"""
import logging
from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def check_hnsw_index_exists(db: Session) -> bool:
    """
    Check if HNSW index exists on document_chunks.embedding
    
    Args:
        db: SQLAlchemy database session
    
    Returns:
        bool: True if index exists, False otherwise
    """
    try:
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'document_chunks' 
                AND indexname = 'idx_chunks_embedding_hnsw'
            )
        """))
        exists = result.scalar()
        return bool(exists)
    except Exception as e:
        logger.error(f"Error checking HNSW index: {e}")
        return False


def get_index_info(db: Session) -> List[Dict[str, str]]:
    """
    Get information about all indexes on document_chunks table
    
    Args:
        db: SQLAlchemy database session
    
    Returns:
        List of dicts with index information
    """
    try:
        result = db.execute(text("""
            SELECT 
                indexname,
                indexdef,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes 
            WHERE tablename = 'document_chunks'
            ORDER BY indexname
        """))
        
        indexes = []
        for row in result:
            indexes.append({
                'name': row[0],
                'definition': row[1],
                'size': row[2]
            })
        
        return indexes
    except Exception as e:
        logger.error(f"Error getting index info: {e}")
        return []


def verify_index_usage(db: Session, user_id: int = 1) -> Dict[str, any]:
    """
    Verify that HNSW index is being used in queries
    
    Tests a sample query and checks if it uses the HNSW index.
    Returns query plan information.
    
    Args:
        db: SQLAlchemy database session
        user_id: User ID to test with (default: 1)
    
    Returns:
        Dict with verification results
    """
    try:
        # Get a sample embedding to test with
        sample = db.execute(text("""
            SELECT embedding 
            FROM document_chunks 
            WHERE user_id = :user_id
            LIMIT 1
        """), {"user_id": user_id}).fetchone()
        
        if not sample:
            return {
                'success': False,
                'message': 'No chunks found for testing',
                'uses_index': False
            }
        
        # Run EXPLAIN to see query plan
        result = db.execute(text("""
            EXPLAIN
            SELECT id, chunk_index
            FROM document_chunks
            WHERE user_id = :user_id
            ORDER BY embedding <=> :test_vector
            LIMIT 5
        """), {"user_id": user_id, "test_vector": str(sample[0])})
        
        plan_lines = [row[0] for row in result]
        plan_text = '\n'.join(plan_lines)
        
        # Check if HNSW index is mentioned in plan
        uses_hnsw = 'idx_chunks_embedding_hnsw' in plan_text
        uses_index_scan = 'Index Scan' in plan_text
        uses_seq_scan = 'Seq Scan' in plan_text
        
        return {
            'success': True,
            'uses_index': uses_hnsw,
            'index_type': 'HNSW' if uses_hnsw else 'Sequential Scan' if uses_seq_scan else 'Other',
            'plan': plan_text,
            'warning': 'Sequential scan detected - index not being used!' if uses_seq_scan else None
        }
        
    except Exception as e:
        logger.error(f"Error verifying index usage: {e}")
        return {
            'success': False,
            'message': str(e),
            'uses_index': False
        }


def get_vector_search_stats(db: Session) -> Dict[str, any]:
    """
    Get statistics about vector search performance
    
    Args:
        db: SQLAlchemy database session
    
    Returns:
        Dict with statistics
    """
    try:
        # Get index usage statistics
        result = db.execute(text("""
            SELECT
                schemaname,
                tablename,
                indexrelname,
                idx_scan as times_used,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched,
                pg_size_pretty(pg_relation_size(indexrelname::regclass)) as size
            FROM pg_stat_user_indexes
            WHERE indexrelname = 'idx_chunks_embedding_hnsw'
        """)).fetchone()
        
        if not result:
            return {
                'success': False,
                'message': 'HNSW index not found'
            }
        
        # Get chunk count
        chunk_count = db.execute(text("SELECT COUNT(*) FROM document_chunks")).scalar()
        
        return {
            'success': True,
            'index_name': result[2],
            'times_used': result[3],
            'tuples_read': result[4],
            'tuples_fetched': result[5],
            'index_size': result[6],
            'total_chunks': chunk_count,
            'avg_tuples_per_scan': result[4] / result[3] if result[3] > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting vector search stats: {e}")
        return {
            'success': False,
            'message': str(e)
        }


def rebuild_hnsw_index(db: Session) -> bool:
    """
    Rebuild HNSW index for optimal performance
    
    Use this after:
    - Bulk data insertion (1000+ new documents)
    - Database performance degradation
    - Major data updates or deletions
    
    WARNING: This can take 5-30 minutes for large datasets
    
    Args:
        db: SQLAlchemy database session
    
    Returns:
        bool: True if successful
    """
    try:
        logger.info("🔨 Rebuilding HNSW index...")
        logger.info("⏳ This may take 5-30 minutes for large datasets...")
        
        db.execute(text("REINDEX INDEX idx_chunks_embedding_hnsw"))
        db.commit()
        
        logger.info("✅ HNSW index rebuilt successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to rebuild HNSW index: {e}")
        return False


# ============================================================
# Manual SQL Commands for Reference
# ============================================================

SQL_COMMANDS = {
    "create_hnsw_index": """
        -- Create HNSW index for fast cosine similarity search
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
        ON document_chunks 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """,
    
    "create_ivfflat_index": """
        -- Create IVFFlat index as alternative (faster build, slightly slower queries)
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat
        ON document_chunks 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """,
    
    "drop_hnsw_index": """
        -- Drop HNSW index (if you need to recreate it)
        DROP INDEX IF EXISTS idx_chunks_embedding_hnsw;
    """,
    
    "check_index_exists": """
        -- Check if HNSW index exists
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'document_chunks' 
        AND indexname = 'idx_chunks_embedding_hnsw';
    """,
    
    "check_index_size": """
        -- Check index size
        SELECT
            indexname,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as size
        FROM pg_indexes
        WHERE tablename = 'document_chunks'
        AND indexname LIKE '%embedding%';
    """,
    
    "verify_index_usage": """
        -- Verify index is being used in queries
        EXPLAIN ANALYZE
        SELECT id, chunk_index
        FROM document_chunks
        WHERE user_id = 1
        ORDER BY embedding <=> (SELECT embedding FROM document_chunks LIMIT 1)
        LIMIT 5;
        
        -- Look for: "Index Scan using idx_chunks_embedding_hnsw"
        -- If you see "Seq Scan", the index is NOT being used!
    """,
    
    "index_usage_stats": """
        -- Get index usage statistics
        SELECT
            schemaname,
            tablename,
            indexrelname,
            idx_scan as times_used,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched,
            pg_size_pretty(pg_relation_size(indexrelname::regclass)) as size
        FROM pg_stat_user_indexes
        WHERE indexrelname = 'idx_chunks_embedding_hnsw';
    """,
    
    "reindex_hnsw": """
        -- Rebuild HNSW index for optimal performance
        -- WARNING: This can take 5-30 minutes!
        REINDEX INDEX idx_chunks_embedding_hnsw;
    """,
    
    "analyze_table": """
        -- Update table statistics for query planner
        ANALYZE document_chunks;
    """,
    
    "tune_hnsw_search": """
        -- Tune HNSW search parameters for better accuracy
        -- Session-level (temporary):
        SET hnsw.ef_search = 100;  -- Default is 40
        
        -- Database-level (permanent):
        ALTER DATABASE document_processor SET hnsw.ef_search = 100;
    """,
    
    "check_pgvector_version": """
        -- Check pgvector extension version
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname = 'vector';
    """,
}


def print_sql_reference():
    """Print all SQL commands for reference"""
    print("\n" + "="*60)
    print("📚 SQL REFERENCE COMMANDS")
    print("="*60 + "\n")
    
    for name, sql in SQL_COMMANDS.items():
        print(f"### {name.upper().replace('_', ' ')}")
        print(sql)
        print()


if __name__ == "__main__":
    # Print SQL reference when run directly
    print_sql_reference()
