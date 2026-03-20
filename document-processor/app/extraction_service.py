"""
Structured extraction service for AVAE compliance verification.

Uses LangChain + OpenAI to extract compliance entities from document text
according to the schema for the given audit_target.
"""
import logging
from typing import Optional

from app.config import settings
from app.schemas_extraction import get_extraction_schema

logger = logging.getLogger(__name__)

# Truncate text to avoid token overflow (gpt-4o context ~128k, keep safe margin)
MAX_TEXT_CHARS = 12_000


def extract_structured(text: str, audit_target: str) -> Optional[dict]:
    """
    Extract compliance entities from document text using LLM + schema.

    Args:
        text: Raw text extracted from PDF
        audit_target: Audit target (epc, companies_house, hm_land_registry)

    Returns:
        Dict of extracted fields, or None if extraction fails/skipped
    """
    if not text or not text.strip():
        logger.warning("Structured extraction skipped: empty text")
        return None

    if not settings.openai_api_key:
        logger.warning("Structured extraction skipped: OPENAI_API_KEY not set")
        return None

    try:
        schema = get_extraction_schema(audit_target)
    except ValueError as e:
        logger.error(f"Structured extraction failed (invalid audit_target): {e}")
        return None

    truncated = text[:MAX_TEXT_CHARS]
    if len(text) > MAX_TEXT_CHARS:
        logger.info(f"Truncated text from {len(text)} to {MAX_TEXT_CHARS} chars for LLM")

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.openai_api_key)
        structured_llm = llm.with_structured_output(schema)

        if audit_target == "financial":
            prompt = (
                "Extract financial and corporate data from this document. "
                "Works for any financial statement: US SEC (10-K, 10-Q), UK, Pakistan PSX, LSE, or other jurisdictions. "
                "Include: company name; exchange or jurisdiction (SEC, PSX, LSE, etc.) if identifiable; "
                "CIK (10-digit) only for US SEC filings; filing type; period end date; revenue; net income; total assets; EPS. "
                "Extract whatever fields are present — leave absent fields empty. "
                "Return only the structured fields, no additional commentary.\n\n"
                "Document text:\n---\n{text}\n---"
            ).format(text=truncated)
        else:
            prompt = (
                "Extract the compliance entities from this document. "
                "Return only the structured fields, no additional commentary.\n\n"
                "Document text:\n---\n{text}\n---"
            ).format(text=truncated)

        result = structured_llm.invoke(prompt)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Structured extraction failed: {e}", exc_info=True)
        return None
