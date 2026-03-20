"""
AVAE LangGraph state definition (Task 3.1).

Shared state passed between nodes. All fields optional for partial updates
(LangGraph merges state after each node).
"""
from typing import TypedDict, Any


class AVAEState(TypedDict, total=False):
    """State for AVAE verification pipeline."""

    # Input (from SQS message)
    task_id: str
    s3_bucket: str
    s3_key: str
    filename: str
    audit_target: str
    prompt: str

    # burst_pdf
    pdf_content: bytes
    temp_file_path: str
    pages: list[dict[str, Any]]

    # classify_pages (Task 4.2: text | image | table | chart)
    page_classifications: list[dict[str, Any]]

    # extract_parallel (Task 4.5: per-page extraction)
    page_extractions: list[dict[str, Any]]  # [{page_num, type, content}]

    # merge_extractions (Task 4.6: combine Markdown + Textract + VLM before normalize)
    extracted_text: str
    page_count: int

    # normalize
    extracted_json: dict[str, Any] | None

    # fetch_api
    api_response: dict[str, Any] | None

    # verify
    verification_status: str
    discrepancy_flags: list[dict[str, Any]]
    fields_compared: list[str]

    # human_review (Task 5.1: HITL state model)
    # Note: "checkpoint_id" is reserved by LangGraph; use hitl_checkpoint_id
    hitl_checkpoint_id: str
    document_preview: dict[str, Any]

    # persist
    metadata: dict[str, Any]

    # Error handling
    error: str
