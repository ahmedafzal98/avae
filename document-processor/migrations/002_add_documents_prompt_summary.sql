-- Migration: Add prompt and summary columns to documents table
-- Purpose: Fix "column documents.prompt does not exist" error
-- The application expects these columns for AI summarization feature
--
-- Run with: psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -f migrations/002_add_documents_prompt_summary.sql

-- Add prompt column (custom prompt for AI summarization at upload time)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS prompt TEXT;

-- Add summary column (AI-generated summary when prompt is provided)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;
