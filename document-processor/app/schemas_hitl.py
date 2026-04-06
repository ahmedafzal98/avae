"""
HITL schemas (Task 5.1).

State model for human-in-the-loop review: checkpoint_id, discrepancies, document_preview.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Discrepancy(BaseModel):
    """Single field mismatch between extracted and API data."""

    field: str = Field(..., description="Field name (e.g. company_number, property_address)")
    extracted: Any = Field(None, description="Value extracted from document")
    api: Any = Field(None, description="Value from external API")
    suggested_action: Optional[str] = Field(
        None,
        description="Override | Manual Correction | Request Client Remediation",
    )


# Task 5.2: HITL API request/response schemas


class OverrideRequest(BaseModel):
    """Request body for POST /hitl/override."""

    checkpoint_id: str = Field(..., description="Task ID (thread_id) for the paused checkpoint")
    field: Optional[str] = Field(None, description="Specific field to override, or omit for all")
    justification: Optional[str] = Field(None, max_length=500, description="Officer justification for override (audit)")


class ManualCorrectionRequest(BaseModel):
    """Request body for POST /hitl/manual-correction."""

    checkpoint_id: str = Field(..., description="Task ID (thread_id) for the paused checkpoint")
    corrections: dict[str, Any] = Field(..., description="Field -> corrected value, e.g. {'company_number': '12345678'}")


class RequestClientRemediationRequest(BaseModel):
    """Request body for POST /hitl/request-client-remediation."""

    checkpoint_id: str = Field(..., description="Task ID (thread_id) for the paused checkpoint")
    message: Optional[str] = Field(None, description="Reason or instructions for client")


class RemediationEmailDraft(BaseModel):
    """Templated email draft for Request Client Remediation (Task 5.6)."""

    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body text")


class HITLResponse(BaseModel):
    """Response for HITL API endpoints."""

    success: bool = True
    message: str = ""
    task_id: Optional[str] = None
    status: Optional[str] = None
    email_draft: Optional[RemediationEmailDraft] = Field(
        None,
        description="Templated email draft (Request Client Remediation only)",
    )


class DocumentPreview(BaseModel):
    """Compact document view for HITL dashboard (Task 5.1)."""

    task_id: str
    filename: str
    audit_target: str
    verification_status: str
    page_count: int
    extracted_json: dict[str, Any] = Field(default_factory=dict)
    api_response: Optional[dict[str, Any]] = None
    extracted_text_preview: str = Field(
        default="",
        description="First N chars of extracted text for preview",
    )
    discrepancy_count: int = Field(0, description="Number of discrepancy flags")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When HITL state was created",
    )


# Task 5.4: Checkpoint listing schemas


class CheckpointListItem(BaseModel):
    """Single checkpoint in the HITL listing."""

    checkpoint_id: str = Field(..., description="Task ID (document ID) for the checkpoint")
    filename: str = Field(..., description="Original filename")
    audit_target: str = Field(
        ...,
        description="Audit target (epc, companies_house, hm_land_registry, financial, vision_poc)",
    )
    status: str = Field(..., description="PENDING_HUMAN_REVIEW or AWAITING_CLIENT_REMEDIATION")
    document_preview: Optional[dict[str, Any]] = Field(
        None,
        description="Compact extracted_json preview for dashboard",
    )
    discrepancy_flags: Optional[list[dict[str, Any]]] = Field(
        None,
        description="List of discrepancy flags from latest audit log",
    )
    created_at: str = Field(..., description="When the document entered HITL state")


class CheckpointListResponse(BaseModel):
    """Paginated response for GET /hitl/checkpoints."""

    checkpoints: list[CheckpointListItem] = Field(default_factory=list)
    total: int = Field(..., description="Total count matching filters")
    page: int = Field(..., description="Current page (1-based)")
    page_size: int = Field(..., description="Items per page")


class CheckpointSummaryResponse(BaseModel):
    """Summary counts for GET /hitl/checkpoints/summary (Phase 7.8)."""

    total: int = Field(..., description="Total documents in HITL queues")
    pending_review: int = Field(..., description="PENDING_HUMAN_REVIEW count")
    awaiting_client: int = Field(..., description="AWAITING_CLIENT_REMEDIATION count")


# Task 5.4: Verification table data (extracted vs API, per field)


class PdfLocation(BaseModel):
    """PDF coordinates for highlighting (react-pdf-viewer HighlightArea format)."""

    page_index: int = Field(..., description="0-based page index")
    left: float = Field(..., description="Left offset as percentage (0-100)")
    top: float = Field(..., description="Top offset as percentage (0-100)")
    width: float = Field(..., description="Width as percentage (0-100)")
    height: float = Field(..., description="Height as percentage (0-100)")


class VerificationFieldRow(BaseModel):
    """Single row for VerificationTable: Field Name, Document Value, API Value, Status."""

    field: str = Field(..., description="Field name (e.g. reference_number, property_address)")
    document_value: Any = Field(None, description="Value extracted from document")
    api_value: Any = Field(None, description="Value from external API")
    status: str = Field(
        ...,
        description="VERIFIED | DISCREPANCY | PENDING",
    )
    pdf_location: PdfLocation | None = Field(
        None,
        description="Location in PDF for highlighting (red=discrepancy, green=verified)",
    )


class DocumentVerificationResponse(BaseModel):
    """Response for GET /documents/{id}/verification (Task 5.4)."""

    document_id: int = Field(..., description="Document ID")
    verification_status: str = Field(
        ...,
        description="Overall status: VERIFIED | DISCREPANCY_FLAG | PENDING",
    )
    audit_target: str = Field(
        ...,
        description="epc | companies_house | hm_land_registry | financial | vision_poc",
    )
    rows: list[VerificationFieldRow] = Field(
        default_factory=list,
        description="Field-by-field comparison for VerificationTable",
    )
    official_record_synced_at: str | None = Field(
        None,
        description="ISO timestamp when official registry data was last synced (for Live sync display)",
    )
