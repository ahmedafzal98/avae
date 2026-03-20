-- Migration 004: Create audit_logs table (Task 1.2)
-- AVAE: Stores verification pipeline output (extracted JSON, API response, verification status)

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    audit_target VARCHAR(50) NOT NULL,
    extracted_json JSONB NOT NULL,
    api_response_json JSONB,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    discrepancy_flags JSONB,
    fields_compared JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_document_id ON audit_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_verification_status ON audit_logs(verification_status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_audit_target ON audit_logs(audit_target);
