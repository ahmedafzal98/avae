#!/usr/bin/env python3
"""
Reprocess old documents to create chunks for RAG
Use this script to add chunks to documents that were uploaded before RAG was implemented
"""

import asyncio
from app.database import SessionLocal
from app.db_models import Document, DocumentChunk
from app.rag_service import rag_service

async def reprocess_document(document_id: int):
    """Reprocess a single document to create chunks"""
    db = SessionLocal()
    try:
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            print(f"❌ Document {document_id} not found")
            return False
        
        if not document.result_text:
            print(f"❌ Document {document_id} has no text content")
            return False
        
        # Check if already has chunks
        existing_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).count()
        
        if existing_chunks > 0:
            print(f"⚠️  Document {document_id} ({document.filename}) already has {existing_chunks} chunks")
            print(f"   Skipping. Delete existing chunks first if you want to reprocess.")
            return False
        
        print(f"🚀 Reprocessing document {document_id}: {document.filename}")
        print(f"   Text length: {len(document.result_text)} characters")
        
        # Run RAG ingestion
        result = rag_service.ingest_document(
            db=db,
            document_id=document.id,
            user_id=document.user_id,
            text=document.result_text,
            metadata={
                "filename": document.filename,
                "s3_key": document.s3_key,
                "page_count": document.page_count or 0
            }
        )
        
        if result["success"]:
            print(f"✅ Successfully created {result['chunks_created']} chunks")
            print(f"   Total tokens: {result.get('total_tokens', 0)}")
            return True
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error reprocessing document {document_id}: {e}")
        return False
    finally:
        db.close()


async def reprocess_all_without_chunks():
    """Find and reprocess all documents that don't have chunks"""
    db = SessionLocal()
    try:
        # Find documents without chunks
        documents = db.query(Document).outerjoin(
            DocumentChunk,
            Document.id == DocumentChunk.document_id
        ).filter(
            Document.status == "COMPLETED",
            Document.result_text.isnot(None),
            DocumentChunk.id.is_(None)
        ).all()
        
        if not documents:
            print("✅ All completed documents already have chunks!")
            return
        
        print(f"📊 Found {len(documents)} documents without chunks:")
        print("=" * 70)
        
        for doc in documents:
            print(f"  - ID {doc.id}: {doc.filename} ({len(doc.result_text or '')} chars)")
        
        print("=" * 70)
        print(f"\n🚀 Starting to reprocess {len(documents)} documents...\n")
        
        # Process each document
        success_count = 0
        for doc in documents:
            success = await reprocess_document(doc.id)
            if success:
                success_count += 1
            print()
        
        print("=" * 70)
        print(f"✅ Reprocessing complete: {success_count}/{len(documents)} succeeded")
        
    finally:
        db.close()


async def main():
    """Main entry point"""
    import sys
    
    if not rag_service.embed_model:
        print("❌ RAG service is not enabled!")
        print("   Make sure OPENAI_API_KEY is set in your .env file")
        return
    
    print("🤖 Document Reprocessing Tool")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        # Reprocess specific document ID
        document_id = int(sys.argv[1])
        await reprocess_document(document_id)
    else:
        # Reprocess all documents without chunks
        await reprocess_all_without_chunks()


if __name__ == "__main__":
    asyncio.run(main())
