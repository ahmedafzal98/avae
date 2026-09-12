-- Migration 005: Add reconciliation support to documents table (Issue #10)
--
-- Fixes documents getting stuck in PENDING forever when the worker crashes
-- between the DB write and the SQS send (dual-write problem). A background
-- reconciliation job re-queues these using retry_count to cap retries, and
-- reuses the existing `status` column with a new 'FAILED_PERMANENT' value
-- once retries are exhausted (see app/reconciliation.py).

ALTER TABLE documents ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;

-- The reconciliation query filters on status, created_at, and retry_count together.
CREATE INDEX IF NOT EXISTS idx_documents_reconciliation
    ON documents (status, created_at, retry_count);
