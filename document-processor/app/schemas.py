"""Pydantic schemas for database models - using Pydantic v2"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============= User Schemas =============

class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a new user"""
    api_key: str = Field(..., min_length=32, description="API key for authentication")


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    api_key: Optional[str] = Field(None, min_length=32)


class UserResponse(UserBase):
    """Schema for user responses"""
    id: int
    api_key: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserWithDocuments(UserResponse):
    """User schema with related documents"""
    documents: List["DocumentResponse"] = []
    
    model_config = ConfigDict(from_attributes=True)


# ============= Document Schemas =============

class DocumentBase(BaseModel):
    """Base document schema with common fields"""
    filename: str
    s3_key: str


class DocumentCreate(DocumentBase):
    """Schema for creating a new document"""
    user_id: int
    status: str = "PENDING"


class DocumentUpdate(BaseModel):
    """Schema for updating a document"""
    status: Optional[str] = Field(None, pattern="^(PENDING|PROCESSING|COMPLETED|FAILED)$")
    result_text: Optional[str] = None
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    extraction_time_seconds: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DocumentResponse(DocumentBase):
    """Schema for document responses"""
    id: int
    user_id: int
    audit_target: Optional[str] = None
    status: str
    result_text: Optional[str] = None
    prompt: Optional[str] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    extraction_time_seconds: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class DocumentWithUser(DocumentResponse):
    """Document schema with related user"""
    user: UserResponse
    
    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Paginated document list response"""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# ============= Task/Job Schemas (for Redis compatibility) =============

class TaskCreate(BaseModel):
    """Schema for creating a task (backward compatible with Redis)"""
    task_id: str
    user_id: int
    filename: str
    s3_key: str
    s3_bucket: str


class TaskUpdate(BaseModel):
    """Schema for updating task status"""
    status: str
    progress: Optional[float] = Field(None, ge=0, le=100)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


# ============= DocumentChunk Schemas (RAG Support) =============

class DocumentChunkBase(BaseModel):
    """Base schema for document chunks"""
    chunk_index: int
    text_content: str


class DocumentChunkCreate(DocumentChunkBase):
    """Schema for creating a document chunk"""
    document_id: int
    user_id: int
    embedding: List[float]
    token_count: Optional[int] = None


class DocumentChunkResponse(DocumentChunkBase):
    """Schema for document chunk responses"""
    id: int
    document_id: int
    user_id: int
    token_count: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DocumentChunkWithEmbedding(DocumentChunkResponse):
    """Schema including embedding vector (use sparingly - large payload)"""
    embedding: List[float]
    
    model_config = ConfigDict(from_attributes=True)


# ============= Chat Schemas (RAG Query Support) =============

class ChatRequest(BaseModel):
    """Schema for chat/query request"""
    question: str = Field(..., min_length=1, max_length=1000, description="User's question")
    document_id: Optional[int] = Field(None, description="Optional: limit search to specific document")
    top_k: int = Field(10, ge=1, le=20, description="Number of chunks to retrieve (1-20)")
    model: str = Field("gpt-4o", description="OpenAI model to use")


class ChatSource(BaseModel):
    """Schema for source citation in chat response"""
    document_id: int
    filename: str
    chunk_index: int
    similarity: float
    preview: str


class ChatUsage(BaseModel):
    """Schema for token usage statistics"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    """Schema for chat/query response"""
    answer: str
    sources: List[ChatSource]
    chunks_found: int
    model: Optional[str] = None
    usage: Optional[ChatUsage] = None
    error: Optional[str] = None
