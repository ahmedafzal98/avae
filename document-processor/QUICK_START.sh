#!/bin/bash
# Quick Start Script for RAG Phase 1 Setup
# Run this to set up your RAG system

set -e  # Exit on error

echo "========================================"
echo "RAG Phase 1 - Quick Setup"
echo "========================================"
echo ""

# Step 1: Install dependencies
echo "📦 Step 1: Installing Python dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Step 2: Check .env file
echo "🔑 Step 2: Checking .env configuration..."
if [ -f .env ]; then
    echo "✅ .env file found"
    
    # Check for OpenAI API key
    if grep -q "OPENAI_API_KEY" .env; then
        echo "✅ OPENAI_API_KEY is configured"
    else
        echo "⚠️  WARNING: OPENAI_API_KEY not found in .env"
        echo "Please add: OPENAI_API_KEY=sk-your-key-here"
    fi
else
    echo "❌ ERROR: .env file not found"
    echo "Please create .env file with required configuration"
    exit 1
fi
echo ""

# Step 3: Setup PostgreSQL
echo "🗄️  Step 3: Setting up PostgreSQL..."
echo "Connecting to database..."

# Enable pgvector extension
psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || {
    echo "⚠️  Could not enable pgvector automatically"
    echo "Please run manually:"
    echo "  psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor"
    echo "  CREATE EXTENSION vector;"
    echo ""
}

# Verify extension
VECTOR_ENABLED=$(psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -t -c "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector';" 2>/dev/null || echo "0")

if [ "$VECTOR_ENABLED" -eq "1" ]; then
    echo "✅ pgvector extension enabled"
else
    echo "❌ pgvector extension not enabled"
    echo "Please enable manually (see RAG_SETUP_GUIDE.md)"
fi
echo ""

# Step 4: Create tables
echo "📋 Step 4: Creating database tables..."
python3 << END
from app.database import init_db
try:
    init_db()
    print("✅ Tables created successfully")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
END
echo ""

# Step 5: Verify setup
echo "🔍 Step 5: Verifying setup..."
echo ""

# Check if document_chunks table exists
CHUNKS_TABLE=$(psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'document_chunks';" 2>/dev/null || echo "0")

if [ "$CHUNKS_TABLE" -eq "1" ]; then
    echo "✅ document_chunks table exists"
else
    echo "❌ document_chunks table not found"
fi

# Check if documents table exists
DOCS_TABLE=$(psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'documents';" 2>/dev/null || echo "0")

if [ "$DOCS_TABLE" -eq "1" ]; then
    echo "✅ documents table exists"
else
    echo "❌ documents table not found"
fi

echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "Next Steps:"
echo "1. Start the FastAPI server:"
echo "   python -m uvicorn app.main:app --reload"
echo ""
echo "2. Start the SQS worker (in a separate terminal):"
echo "   python -m app.sqs_worker"
echo ""
echo "3. Upload a test document and watch the worker logs"
echo ""
echo "4. After first document, create vector index:"
echo "   psql -h 127.0.0.1 -p 5433 -U docuser -d document_processor"
echo "   CREATE INDEX idx_document_chunks_embedding_ivfflat"
echo "   ON document_chunks USING ivfflat (embedding vector_cosine_ops)"
echo "   WITH (lists = 100);"
echo ""
echo "📚 Documentation:"
echo "   - Setup Guide: RAG_SETUP_GUIDE.md"
echo "   - Data Flow: RAG_DATA_FLOW.md"
echo "   - Summary: PHASE_1_COMPLETE.md"
echo ""
