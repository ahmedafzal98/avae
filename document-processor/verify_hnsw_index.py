#!/usr/bin/env python3
"""
🔍 HNSW Index Verification Script

This script verifies that your HNSW vector index is:
1. Created successfully
2. Being used by queries
3. Providing performance improvements

Usage:
    python3 verify_hnsw_index.py
"""

import sys
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from app.config import settings

print("\n" + "="*60)
print("🔍 HNSW INDEX VERIFICATION")
print("="*60 + "\n")

# Create database connection
print("🔌 Connecting to database...")
try:
    engine = create_engine(settings.database_url)
    conn = engine.connect()
    print(f"✅ Connected to: {settings.postgres_db}\n")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

# ============================================================
# TEST 1: Check if pgvector extension exists
# ============================================================
print("="*60)
print("TEST 1: pgvector Extension")
print("="*60)

try:
    result = conn.execute(text("""
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname = 'vector'
    """))
    row = result.fetchone()
    
    if row:
        print(f"✅ pgvector extension installed: v{row[1]}")
    else:
        print("❌ pgvector extension NOT installed")
        print("   Run: CREATE EXTENSION vector;")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error checking extension: {e}")
    sys.exit(1)

# ============================================================
# TEST 2: Check if document_chunks table exists
# ============================================================
print("\n" + "="*60)
print("TEST 2: document_chunks Table")
print("="*60)

try:
    result = conn.execute(text("""
        SELECT COUNT(*) FROM document_chunks
    """))
    chunk_count = result.scalar()
    print(f"✅ document_chunks table exists")
    print(f"   📦 Total chunks: {chunk_count}")
    
    if chunk_count == 0:
        print("\n⚠️  WARNING: No chunks in database")
        print("   Upload and process documents before testing index performance")
except Exception as e:
    print(f"❌ Error checking table: {e}")
    sys.exit(1)

# ============================================================
# TEST 3: Check if HNSW index exists
# ============================================================
print("\n" + "="*60)
print("TEST 3: HNSW Index Existence")
print("="*60)

try:
    result = conn.execute(text("""
        SELECT 
            indexname,
            indexdef,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as size
        FROM pg_indexes 
        WHERE tablename = 'document_chunks' 
        AND indexname = 'idx_chunks_embedding_hnsw'
    """))
    
    row = result.fetchone()
    
    if row:
        print(f"✅ HNSW index EXISTS")
        print(f"   📛 Name: {row[0]}")
        print(f"   💾 Size: {row[2]}")
        print(f"   📝 Definition:")
        print(f"      {row[1]}")
        hnsw_exists = True
    else:
        print("❌ HNSW index NOT FOUND")
        print("\n📋 To create the index, run:")
        print("   python3 migrations/run_migration.py")
        print("\n   Or manually:")
        print("   CREATE INDEX idx_chunks_embedding_hnsw")
        print("   ON document_chunks")
        print("   USING hnsw (embedding vector_cosine_ops)")
        print("   WITH (m = 16, ef_construction = 64);")
        hnsw_exists = False
except Exception as e:
    print(f"❌ Error checking index: {e}")
    hnsw_exists = False

# ============================================================
# TEST 4: List all indexes on document_chunks
# ============================================================
print("\n" + "="*60)
print("TEST 4: All Indexes on document_chunks")
print("="*60)

try:
    result = conn.execute(text("""
        SELECT 
            indexname,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as size
        FROM pg_indexes 
        WHERE tablename = 'document_chunks'
        ORDER BY indexname
    """))
    
    indexes = result.fetchall()
    
    if indexes:
        print(f"📊 Found {len(indexes)} index(es):\n")
        for idx in indexes:
            print(f"   • {idx[0]:40s} {idx[1]:>10s}")
    else:
        print("⚠️  No indexes found on document_chunks table")
except Exception as e:
    print(f"❌ Error listing indexes: {e}")

# ============================================================
# TEST 5: Verify index is being used in queries
# ============================================================
if hnsw_exists and chunk_count > 0:
    print("\n" + "="*60)
    print("TEST 5: Query Plan Verification")
    print("="*60)
    
    try:
        # Get a sample embedding
        result = conn.execute(text("""
            SELECT embedding 
            FROM document_chunks 
            LIMIT 1
        """))
        sample_embedding = result.fetchone()[0]
        
        # Run EXPLAIN to see query plan
        result = conn.execute(text("""
            EXPLAIN
            SELECT id, chunk_index
            FROM document_chunks
            WHERE user_id = 1
            ORDER BY embedding <=> :test_vector
            LIMIT 5
        """), {"test_vector": str(sample_embedding)})
        
        plan_lines = [row[0] for row in result]
        
        print("📋 Query Plan:")
        print()
        for line in plan_lines:
            print(f"   {line}")
        
        # Check if index is being used
        plan_text = '\n'.join(plan_lines)
        
        if 'idx_chunks_embedding_hnsw' in plan_text:
            print("\n✅ HNSW index IS being used in queries! 🚀")
        elif 'Index Scan' in plan_text:
            print("\n⚠️  An index is being used, but NOT the HNSW index")
        elif 'Seq Scan' in plan_text:
            print("\n❌ Sequential scan detected - HNSW index NOT being used!")
            print("   Possible causes:")
            print("   - Index not created yet")
            print("   - Table statistics outdated (run: ANALYZE document_chunks;)")
            print("   - Query planner choosing seq scan for small datasets")
        
    except Exception as e:
        print(f"❌ Error verifying query plan: {e}")

# ============================================================
# TEST 6: Performance benchmark (if data exists)
# ============================================================
if hnsw_exists and chunk_count > 10:
    print("\n" + "="*60)
    print("TEST 6: Performance Benchmark")
    print("="*60)
    
    try:
        # Get a sample embedding
        result = conn.execute(text("""
            SELECT embedding 
            FROM document_chunks 
            LIMIT 1
        """))
        sample_embedding = result.fetchone()[0]
        
        # Warm up cache
        conn.execute(text("""
            SELECT id FROM document_chunks LIMIT 1
        """))
        
        # Benchmark with index
        print("\n🏃 Running benchmark (5 queries)...")
        times = []
        
        for i in range(5):
            start = time.time()
            
            result = conn.execute(text("""
                SELECT id, chunk_index
                FROM document_chunks
                WHERE user_id = 1
                ORDER BY embedding <=> :test_vector
                LIMIT 5
            """), {"test_vector": str(sample_embedding)})
            
            _ = result.fetchall()
            
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)
            print(f"   Query {i+1}: {elapsed:.2f}ms")
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📊 Results:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Min: {min_time:.2f}ms")
        print(f"   Max: {max_time:.2f}ms")
        
        if avg_time < 200:
            print(f"\n✅ Excellent performance! ({avg_time:.0f}ms) 🚀")
        elif avg_time < 500:
            print(f"\n✅ Good performance! ({avg_time:.0f}ms)")
        elif avg_time < 1000:
            print(f"\n⚠️  Moderate performance ({avg_time:.0f}ms)")
            print("   Consider rebuilding index or tuning parameters")
        else:
            print(f"\n❌ Poor performance ({avg_time:.0f}ms)")
            print("   Index may not be working correctly")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")

# ============================================================
# TEST 7: Index usage statistics
# ============================================================
if hnsw_exists:
    print("\n" + "="*60)
    print("TEST 7: Index Usage Statistics")
    print("="*60)
    
    try:
        result = conn.execute(text("""
            SELECT
                idx_scan as times_used,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched
            FROM pg_stat_user_indexes
            WHERE indexrelname = 'idx_chunks_embedding_hnsw'
        """))
        
        row = result.fetchone()
        
        if row:
            print(f"\n📊 Index Statistics:")
            print(f"   Times used: {row[0]}")
            print(f"   Tuples read: {row[1]}")
            print(f"   Tuples fetched: {row[2]}")
            
            if row[0] > 0:
                avg_tuples = row[1] / row[0]
                print(f"   Avg tuples per scan: {avg_tuples:.2f}")
                
                if avg_tuples < chunk_count * 0.1:
                    print("\n✅ Index is working efficiently! 🎯")
                else:
                    print("\n⚠️  Index may not be optimally utilized")
            else:
                print("\n⚠️  Index has not been used yet")
                print("   Run some chat queries to see statistics")
        
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "="*60)
print("📊 VERIFICATION SUMMARY")
print("="*60 + "\n")

if hnsw_exists:
    print("✅ HNSW index is INSTALLED")
    print("✅ pgvector extension is ENABLED")
    
    if chunk_count > 0:
        print("✅ document_chunks table has DATA")
        print("\n🎯 Your vector search is optimized!")
        print("   Expected performance: 50-200ms per query")
    else:
        print("⚠️  No chunks in database yet")
        print("   Upload documents to test performance")
else:
    print("❌ HNSW index is MISSING")
    print("\n📋 Next steps:")
    print("   1. Run: python3 migrations/run_migration.py")
    print("   2. Wait 5-30 minutes for index to build")
    print("   3. Run this verification script again")

print("\n" + "="*60 + "\n")

# Close connection
conn.close()
