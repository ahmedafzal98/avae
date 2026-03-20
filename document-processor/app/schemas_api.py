"""Pydantic models for request/response validation"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from uuid import UUID
import os


class ProcessingTask(BaseModel):
    """Task payload sent to queue - Type-safe"""
    task_id: str
    file_path: str
    filename: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class TaskStatusResponse(BaseModel):
    """API response for task status"""
    task_id: str
    status: Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED", "PENDING_HUMAN_REVIEW", "AWAITING_CLIENT_REMEDIATION", "EXPIRED"]
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    filename: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class PDFMetadata(BaseModel):
    """Extracted PDF metadata"""
    author: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    subject: Optional[str] = None
    title: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None


class PDFExtractionResult(BaseModel):
    """Complete PDF extraction result"""
    task_id: str
    filename: str
    page_count: int
    text: str
    metadata: PDFMetadata
    extraction_time_seconds: float
    summary: Optional[str] = None


class UploadResponse(BaseModel):
    """Response after file upload"""
    task_ids: List[str]
    total_files: int
    message: str


class TaskListResponse(BaseModel):
    """Paginated task list response"""
    tasks: List[TaskStatusResponse]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    redis_connected: bool
    celery_workers: int
    queue_depth: int
    timestamp: str


class AuditLogListItem(BaseModel):
    """Single row for audit log table (Phase 7.2)."""
    id: int = Field(..., description="Audit log entry ID")
    document_id: int = Field(..., description="Document ID")
    created_at: str = Field(..., description="Timestamp (ISO)")
    audit_target: str = Field(..., description="epc | companies_house | hm_land_registry | financial")
    verification_status: str = Field(..., description="VERIFIED | DISCREPANCY_FLAG | PENDING_HUMAN_REVIEW | etc.")
    filename: str = Field(default="", description="Document filename")


class AuditLogListResponse(BaseModel):
    """Paginated response for GET /audit-logs (Phase 7.6)."""
    items: List[AuditLogListItem] = Field(default_factory=list)
    total: int = Field(..., description="Total count matching filters")
    page: int = Field(..., description="Current page (1-based)")
    page_size: int = Field(..., description="Items per page")


class AuditHealthStatsResponse(BaseModel):
    """Response for GET /audit-logs/stats (Phase 7.7)."""
    total: int = Field(..., description="Total audit log entries in period")
    verified: int = Field(..., description="Count with VERIFIED status")
    discrepancy_flag: int = Field(..., description="Count with DISCREPANCY_FLAG")
    pending_human_review: int = Field(..., description="Count with PENDING_HUMAN_REVIEW")
    success_rate: float = Field(..., description="Verified / total as percentage (0–100)")
    trend_direction: str = Field("stable", description="up | down | stable")
    trend_value: float = Field(0.0, description="Absolute percentage point change vs previous period")


class AuditLogDetailResponse(BaseModel):
    """Full audit log entry for expand row (Phase 7.9)."""
    id: int
    document_id: int
    created_at: str
    audit_target: str
    verification_status: str
    filename: str = ""
    extracted_json: Dict[str, Any] = Field(default_factory=dict)
    api_response_json: Optional[Dict[str, Any]] = None
    discrepancy_flags: Optional[List[Any]] = None
    fields_compared: Optional[List[Any]] = None


class FileUploadValidator:
    """Validator for file uploads"""
    
    ALLOWED_EXTENSIONS = {".pdf"}
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Check if filename has valid PDF extension"""
        _, ext = os.path.splitext(filename.lower())
        return ext in FileUploadValidator.ALLOWED_EXTENSIONS
    
    @staticmethod
    def validate_file_size(file_size: int, max_size_mb: int) -> bool:
        """Check if file size is within limit"""
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes
    
    @staticmethod
    def validate_file_count(count: int, max_count: int) -> bool:
        """Check if file count is within limit"""
        return 0 < count <= max_count
