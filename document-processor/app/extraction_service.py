"""
Structured extraction service for AVAE compliance verification.

Uses LangChain + OpenAI to extract compliance entities from document text
according to the schema for the given audit_target.
"""
import logging

from app.config import settings
from app.extraction_utils import strip_empty_extraction_fields
from app.schemas_extraction import get_extraction_schema

logger = logging.getLogger(__name__)

# Truncate text to avoid token overflow (gpt-4o context ~128k, keep safe margin)
MAX_TEXT_CHARS = 12_000


def _clear_llm_null_strings(dumped: dict | None) -> dict | None:
    """The model's JSON response occasionally emits the literal string "null"
    (quoted text) for an uncertain Optional[str] field instead of the JSON null
    literal — the schema allows null, but structured-output sampling doesn't
    always take it. Treat that the same as no value, at the source, so a stray
    "null" string never reaches verification/storage as if it were real data."""
    if not isinstance(dumped, dict):
        return dumped
    return {
        k: (None if isinstance(v, str) and v.strip().lower() == "null" else v)
        for k, v in dumped.items()
    }


def extract_structured(text: str, audit_target: str, return_usage: bool = False):
    """
    Extract compliance entities from document text using LLM + schema.

    Args:
        text: Raw text extracted from PDF
        audit_target: Audit target (epc, companies_house, hm_land_registry)
        return_usage: If True, also return the LLM call's token usage (for cost
            tracking in batch/test tooling). Default False preserves the original
            return type exactly, so existing callers are unaffected.

    Returns:
        Dict of extracted fields, or None if extraction fails/skipped.
        If return_usage=True, returns (dict_or_None, usage_dict_or_None) instead,
        where usage_dict has input_tokens/output_tokens/total_tokens.
    """
    empty = (None, None) if return_usage else None

    if not text or not text.strip():
        logger.warning("Structured extraction skipped: empty text")
        return empty

    if not settings.openai_api_key:
        logger.warning("Structured extraction skipped: OPENAI_API_KEY not set")
        return empty

    try:
        schema = get_extraction_schema(audit_target)
    except ValueError as e:
        logger.error(f"Structured extraction failed (invalid audit_target): {e}")
        return empty

    truncated = text[:MAX_TEXT_CHARS]
    if len(text) > MAX_TEXT_CHARS:
        logger.info(f"Truncated text from {len(text)} to {MAX_TEXT_CHARS} chars for LLM")

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.openai_api_key)
        structured_llm = llm.with_structured_output(schema, include_raw=True) if return_usage else llm.with_structured_output(schema)

        if audit_target == "financial":
            prompt = (
                "Extract financial and corporate data from this document. "
                "Documents may be in Arabic, English, or other languages; preserve non-English text as written. "
                "Works for any financial statement: US SEC (10-K, 10-Q), UK, Pakistan PSX, LSE, or other jurisdictions. "
                "Include: company name; exchange or jurisdiction (SEC, PSX, LSE, etc.) if identifiable; "
                "CIK (10-digit) only for US SEC filings; filing type; period end date; revenue; net income; total assets; EPS. "
                "Extract whatever fields are present — leave absent fields empty. "
                "Return only the structured fields, no additional commentary.\n\n"
                "Document text:\n---\n{text}\n---"
            ).format(text=truncated)
        elif audit_target == "vision_poc":
            prompt = (
                "Extract identity and document fields from the text below (OCR fallback when vision is unavailable). "
                "The document may be Arabic, English, or mixed; preserve Arabic text exactly. "
                "Leave fields empty if not found. Do not invent values.\n\n"
                "Document text:\n---\n{text}\n---"
            ).format(text=truncated)
        else:
            prompt = (
                "Extract the compliance entities from this document. "
                "The document may be in Arabic, English, or mixed Arabic and English; preserve Arabic text exactly as written. "
                "Return only the structured fields, no additional commentary.\n\n"
                "Document text:\n---\n{text}\n---"
            ).format(text=truncated)

        result = structured_llm.invoke(prompt)

        if return_usage:
            parsed = result.get("parsed")
            usage = getattr(result.get("raw"), "usage_metadata", None)
            dumped = parsed.model_dump() if parsed else None
        else:
            usage = None
            dumped = result.model_dump()

        dumped = _clear_llm_null_strings(dumped)

        if audit_target == "vision_poc" and dumped is not None:
            dumped = strip_empty_extraction_fields(dumped) or None

        return (dumped, usage) if return_usage else dumped
    except Exception as e:
        logger.error(f"Structured extraction failed: {e}", exc_info=True)
        return empty
