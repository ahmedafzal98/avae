"""RAG Service - Handles chunking, embedding, and vector storage for RAG functionality"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db_models import DocumentChunk

# Configure logging
logger = logging.getLogger(__name__)


class RAGService:
    """
    Service for RAG (Retrieval-Augmented Generation) operations
    
    Handles:
    - Text chunking using LlamaIndex
    - Embedding generation using OpenAI
    - Storage of chunks and embeddings in PostgreSQL
    """
    
    def __init__(self):
        """Initialize RAG service with embedding model and chunker"""
        # Check if OpenAI API key is configured
        if not settings.openai_api_key:
            logger.warning("⚠️  OpenAI API key not configured - RAG ingestion will be skipped")
            self.embed_model = None
        else:
            # Initialize OpenAI embedding model
            self.embed_model = OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key,
                embed_batch_size=100  # Batch multiple embeddings for efficiency
            )
        
        # SentenceSplitter handles prose/text sections and oversized nodes
        self.text_splitter = SentenceSplitter(
            chunk_size=1024,
            chunk_overlap=200,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[^,.;。？！]+[,.;。？！]?",
        )

        # MarkdownNodeParser — no LLM required, works for both native and scanned PDFs.
        # Splits at markdown heading boundaries (# / ## / ### …).
        # Tables under a heading stay in the same section node — never split mid-table.
        # Nodes that exceed the token budget are then split by text_splitter.
        try:
            self.md_parser = MarkdownNodeParser()
            logger.info("✅ MarkdownNodeParser ready (heading-based sections, tables preserved)")
        except Exception as e:
            logger.warning(f"⚠️  MarkdownNodeParser unavailable ({e}), will use SentenceSplitter only")
            self.md_parser = None

        if self.embed_model:
            logger.info("✅ RAG Service initialized with text-embedding-3-small")
        else:
            logger.info("⚠️  RAG Service initialized WITHOUT embeddings (OpenAI key missing)")
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Two-pass chunking pipeline:

        Pass 1 — MarkdownNodeParser (no LLM, no external deps):
          Splits the LlamaParse markdown output at heading boundaries.
          Each section (heading + its content) becomes one node.
          Tables within a section are never split.
          Works identically for native PDFs and scanned/OCR PDFs.

        Pass 2 — SentenceSplitter on oversized nodes:
          Any section node that exceeds ~800 words is split further by
          SentenceSplitter so embeddings stay semantically precise.

        Falls back to pure SentenceSplitter if MarkdownNodeParser is unavailable.

        Args:
            text: Markdown text from LlamaParse
            metadata: Optional metadata to attach to every chunk

        Returns:
            List of chunk dicts: {chunk_index, text, metadata}
        """
        if not text or not text.strip():
            logger.warning("⚠️  Empty text provided for chunking")
            return []

        doc = LlamaDocument(text=text, metadata=metadata or {})

        # Pass 1: section-level split by markdown headings
        section_nodes = []
        if self.md_parser is not None:
            try:
                section_nodes = self.md_parser.get_nodes_from_documents([doc])
            except Exception as e:
                logger.warning(f"⚠️  MarkdownNodeParser failed ({e}), falling back to SentenceSplitter")

        # If MarkdownNodeParser produced nothing, use SentenceSplitter directly
        if not section_nodes:
            logger.info("📄 Using SentenceSplitter (no markdown sections detected)")
            section_nodes = self.text_splitter.get_nodes_from_documents([doc])

        # Pass 2: split oversized section nodes (e.g. very long Notes sections)
        # Tables are typically short enough that they won't be split here.
        final_nodes = []
        for node in section_nodes:
            content = node.get_content()
            if not content or not content.strip():
                continue
            word_count = len(content.split())
            if word_count > 800:
                # Section too large — split into sentence chunks
                sub_doc = LlamaDocument(text=content, metadata=node.metadata or {})
                sub_nodes = self.text_splitter.get_nodes_from_documents([sub_doc])
                final_nodes.extend(sub_nodes)
            else:
                final_nodes.append(node)

        # Ultimate fallback: if still empty, run plain SentenceSplitter on full text
        if not final_nodes:
            logger.warning("⚠️  All passes produced 0 nodes — running SentenceSplitter on full text")
            final_nodes = self.text_splitter.get_nodes_from_documents([doc])

        logger.info(f"📄 Chunked into {len(final_nodes)} nodes (MarkdownNodeParser + SentenceSplitter pipeline)")

        chunks = []
        for idx, node in enumerate(final_nodes):
            content = node.get_content()
            if not content or not content.strip():
                continue
            node_meta = {**node.metadata} if node.metadata else {}
            chunks.append({
                "chunk_index": idx,
                "text": content,
                "metadata": node_meta,
            })

        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using OpenAI
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors (each is a list of 1536 floats)
        """
        if not self.embed_model:
            logger.error("❌ Cannot generate embeddings: OpenAI API key not configured")
            raise ValueError("OpenAI API key not configured. Add OPENAI_API_KEY to .env file")
        
        if not texts:
            logger.warning("⚠️  No texts provided for embedding")
            return []
        
        logger.info(f"🔢 Generating embeddings for {len(texts)} chunks...")
        
        try:
            # Generate embeddings (automatically batches internally)
            embeddings = self.embed_model.get_text_embedding_batch(texts)
            
            logger.info(f"✅ Generated {len(embeddings)} embeddings")
            return embeddings
        
        except Exception as e:
            logger.error(f"❌ Error generating embeddings: {e}")
            raise
    
    async def store_chunks_in_db(
        self,
        db: AsyncSession,
        document_id: int,
        user_id: int,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> int:
        """
        Store chunks and their embeddings in the database (async).

        Args:
            db: SQLAlchemy async database session
            document_id: ID of the parent document
            user_id: ID of the user (for multi-tenancy)
            chunks: List of chunk dictionaries from chunk_text()
            embeddings: List of embedding vectors from generate_embeddings()

        Returns:
            Number of chunks stored
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings"
            )
        
        logger.info(f"💾 Storing {len(chunks)} chunks for document {document_id}...")
        
        try:
            chunk_records = [
                DocumentChunk(
                    document_id=document_id,
                    user_id=user_id,
                    chunk_index=chunk_data["chunk_index"],
                    text_content=chunk_data["text"],
                    embedding=embedding,
                    token_count=len(chunk_data["text"].split()),
                )
                for chunk_data, embedding in zip(chunks, embeddings)
            ]
            
            db.add_all(chunk_records)
            await db.commit()
            
            logger.info(f"✅ Stored {len(chunk_records)} chunks in database")
            return len(chunk_records)
        
        except Exception as e:
            logger.error(f"❌ Error storing chunks: {e}")
            await db.rollback()
            raise
    
    async def ingest_document(
        self,
        db: AsyncSession,
        document_id: int,
        user_id: int,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Complete RAG ingestion pipeline: chunk → embed → store (async).

        chunk_text() and generate_embeddings() are CPU/IO-bound but handled
        synchronously inside; only the DB write is awaited.

        Args:
            db: SQLAlchemy async database session
            document_id: ID of the document in the documents table
            user_id: ID of the user who owns the document
            text: Full extracted text from LlamaParse
            metadata: Optional metadata (filename, page_count, etc.)

        Returns:
            Dictionary with ingestion statistics
        """
        start_time = datetime.now()
        
        logger.info(f"🚀 Starting RAG ingestion for document {document_id}")
        logger.info(f"   Text length: {len(text)} characters")
        
        if not self.embed_model:
            logger.warning("⚠️  Skipping RAG ingestion: OpenAI API key not configured")
            return {
                "success": False,
                "chunks_created": 0,
                "error": "OpenAI API key not configured. Add OPENAI_API_KEY to .env file"
            }
        
        try:
            # Step 1: Chunk the text (sync — CPU-bound)
            chunks = self.chunk_text(text, metadata)
            
            if not chunks:
                logger.warning("⚠️  No chunks created, skipping embedding")
                return {
                    "success": False,
                    "chunks_created": 0,
                    "error": "No chunks created from text"
                }
            
            # Step 2: Generate embeddings (sync — OpenAI batch call)
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = self.generate_embeddings(chunk_texts)
            
            # Step 3: Store in database (async — awaited DB write)
            chunks_stored = await self.store_chunks_in_db(
                db=db,
                document_id=document_id,
                user_id=user_id,
                chunks=chunks,
                embeddings=embeddings
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ RAG ingestion completed in {duration:.2f}s")
            logger.info(f"   Chunks: {chunks_stored}")
            logger.info(f"   Avg chunk size: {len(text) // chunks_stored} chars")
            
            return {
                "success": True,
                "chunks_created": chunks_stored,
                "total_tokens": sum(chunk.get("token_count", 0) for chunk in chunks),
                "duration_seconds": round(duration, 2)
            }
        
        except Exception as e:
            logger.error(f"❌ RAG ingestion failed: {e}")
            return {
                "success": False,
                "chunks_created": 0,
                "error": str(e)
            }
    
    def search_similar_chunks(
        self,
        db: AsyncSession,
        user_id: int,
        query: str,
        top_k: int = 5,
        document_id: int = None
    ) -> List[DocumentChunk]:
        """
        Search for chunks similar to the query (for RAG chat)
        
        Note: This is a placeholder for Phase 2. For now, it shows the structure.
        In Phase 2, we'll implement the actual vector similarity search.
        
        Args:
            db: SQLAlchemy database session
            user_id: User ID for multi-tenancy filtering
            query: User's question
            top_k: Number of chunks to retrieve
            document_id: Optional - limit search to specific document
        
        Returns:
            List of similar DocumentChunk objects
        """
        logger.info(f"🔍 Searching for chunks similar to: '{query[:50]}...'")
        logger.info("⚠️  Full vector search will be implemented in Phase 2")
        
        # Placeholder: Will implement proper cosine similarity search in Phase 2
        # For now, this function structure shows what's coming
        
        return []


# Global RAG service instance
rag_service = RAGService()
