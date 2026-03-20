-- Migration: Enable pgvector extension and create vector indexes
-- Description: Prepares PostgreSQL for RAG functionality with vector similarity search
-- Date: 2026-02-17

-- ============================================================
-- STEP 1: Enable pgvector extension
-- ============================================================
-- This must be run by a superuser or database owner
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is installed
SELECT * FROM pg_extension WHERE extname = 'vector';


-- ============================================================
-- STEP 2: Create vector index for fast similarity search
-- ============================================================
-- Note: This should be run AFTER the document_chunks table is created
-- and has some data in it for optimal index building

-- Option 1: HNSW Index (Recommended for production - faster queries)
-- Use this when you have > 100k vectors
-- CREATE INDEX idx_document_chunks_embedding_hnsw 
-- ON document_chunks 
-- USING hnsw (embedding vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- Option 2: IVFFlat Index (Good for < 100k vectors - faster to build)
-- Use this for initial development
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_ivfflat 
ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Note: You can drop the ivfflat index and create hnsw later:
-- DROP INDEX idx_document_chunks_embedding_ivfflat;
-- CREATE INDEX idx_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops);


-- ============================================================
-- STEP 3: Create index on metadata for fast user filtering
-- ============================================================
-- This ensures user isolation queries are fast
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_document 
ON document_chunks (user_id, document_id);


-- ============================================================
-- STEP 4: Verify setup
-- ============================================================
-- Check if indexes were created
SELECT 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'document_chunks'
ORDER BY indexname;


-- ============================================================
-- PERFORMANCE TUNING (Optional)
-- ============================================================
-- Analyze table for query optimizer
ANALYZE document_chunks;

-- Check table statistics
SELECT 
    schemaname,
    tablename,
    n_tup_ins as "rows_inserted",
    n_tup_upd as "rows_updated",
    n_tup_del as "rows_deleted",
    n_live_tup as "live_rows"
FROM pg_stat_user_tables
WHERE tablename = 'document_chunks';
