-- PostgreSQL initialization script for Document Processor
-- This script runs automatically when the container is first created

-- Note: The database 'document_processor' and user 'docuser' are created
-- automatically by the POSTGRES_DB and POSTGRES_USER environment variables
-- in docker-compose.yml

-- Grant all privileges to docuser (already done by default, but explicit is better)
GRANT ALL PRIVILEGES ON DATABASE document_processor TO docuser;

-- The actual tables will be created by SQLAlchemy via app/database.py init_db()
-- This keeps the schema definition in Python code (single source of truth)

-- Optional: Create pgvector extension if you plan to use it later
CREATE EXTENSION IF NOT EXISTS vector;

-- Insert a default test user for development (optional)
-- Uncomment after first run when tables are created by SQLAlchemy
-- INSERT INTO users (email, api_key) 
-- VALUES ('test@example.com', 'test_api_key_12345678901234567890')
-- ON CONFLICT (email) DO NOTHING;
