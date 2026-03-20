-- Migration 003: Add audit_target to documents (Task 1.1)
-- AVAE: Audit target for compliance verification (epc, companies_house, hm_land_registry)

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS audit_target VARCHAR(50) DEFAULT 'epc';
