"""SQLAlchemy ORM models for PostgreSQL database"""
from datetime import datetime
from typing import List
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index, text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


class User(Base):
    """User model - stores API users and their credentials"""
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # User fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Document(Base):
    """Document model - stores uploaded documents and processing status"""
    __tablename__ = "documents"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to user
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Document fields
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)

    # AVAE: Audit target for compliance verification (epc, companies_house, hm_land_registry)
    audit_target: Mapped[str | None] = mapped_column(String(50), nullable=True, default="epc")

    # Status: PENDING, PROCESSING, COMPLETED, FAILED
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        index=True
    )
    
    # Result text - extracted content (can be large)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Optional prompt supplied at upload time for AI summarization
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # AI-generated summary produced by the worker (populated only when prompt is given)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Error message if processing failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Processing metadata
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_time_seconds: Mapped[float | None] = mapped_column(nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_user_status", "user_id", "status"),
        Index("idx_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


class AuditLog(Base):
    """
    AVAE: Audit log for verification pipeline output.
    Stores extracted JSON, API response, verification status, and discrepancy flags.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    audit_target: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    extracted_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    api_response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )
    discrepancy_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    fields_compared: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    document: Mapped["Document"] = relationship("Document", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_document_id", "document_id"),
        Index("idx_audit_logs_verification_status", "verification_status"),
        Index("idx_audit_logs_audit_target", "audit_target"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, document_id={self.document_id}, status={self.verification_status})>"


class DocumentChunk(Base):
    """
    DocumentChunk model - stores text chunks and embeddings for RAG
    
    This table enables:
    - Vector similarity search for chat/RAG functionality
    - Multi-tenancy via user_id filtering
    - Document reconstruction via chunk_index ordering
    
    HNSW Index Configuration:
    - Algorithm: Hierarchical Navigable Small World (HNSW)
    - Operator: vector_cosine_ops (for <=> cosine distance)
    - Parameters:
      * m=16: Bidirectional links per node (balance between speed and accuracy)
      * ef_construction=64: Dynamic candidate list size during build
    
    Performance:
    - 20-60x faster than sequential scan
    - 50-100ms queries on 10K chunks (vs 2-3s without index)
    - Scales to millions of vectors
    
    Raw SQL equivalent (for manual creation):
    
        CREATE INDEX idx_chunks_embedding_hnsw 
        ON document_chunks 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    
    Note: HNSW index creation can take 5-30 minutes for large datasets.
    SQLAlchemy will attempt to create this during init_db(), but if your
    dataset is large, consider running the migration script instead:
    
        python3 migrations/run_migration.py
    """
    __tablename__ = "document_chunks"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to document
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Foreign key to user (denormalized for fast filtering)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Chunk ordering within document
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # The actual text content of the chunk
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)
    embedding: Mapped[List[float]] = mapped_column(Vector(1536), nullable=False)
    
    # Token count for this chunk (useful for cost tracking)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP")
    )
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    
    # Indexes for efficient RAG queries
    __table_args__ = (
        # Standard B-tree indexes
        Index("idx_chunk_user_id", "user_id"),
        Index("idx_chunk_document_chunk", "document_id", "chunk_index"),
        
        # HNSW vector index for fast cosine similarity search
        # Parameters optimized for document embedding workloads (1K-1M vectors)
        Index(
            "idx_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={
                "m": 16,                # Bidirectional links per node (16 is optimal for most use cases)
                "ef_construction": 64   # Build-time search depth (64 balances build time vs accuracy)
            },
            postgresql_ops={
                "embedding": "vector_cosine_ops"  # Use cosine distance for <=> operator
            }
        ),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
