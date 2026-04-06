"""
Multimodal structured extraction using GPT-4o vision on PDF page images.

Used when audit_target is vision_poc (client POC / Arabic IDs / scans without relying on OCR-only text).
"""
import base64
import io
import logging
from typing import Optional

from app.config import settings
from app.extraction_utils import strip_empty_extraction_fields
from app.schemas_extraction import get_extraction_schema

logger = logging.getLogger(__name__)

_VISION_PROMPT = """You are an expert document reader. The images are consecutive pages of ONE document — often a Gulf residence permit (Iqama), national ID, or a bilingual English/Arabic contract or form.

Rules:
- Transcribe only what you can clearly read. Preserve Arabic text exactly as written (do not translate names or addresses unless both appear).
- For id_number, passport_number, date_of_birth, issue_date, and expiry_date: copy digits and date layout as printed (Western 0–9, Arabic-Indic ٠–٩, Hijri/Gregorian labels). Do not rewrite dates into English month names if the document shows another format.
- Fill structured fields only when the information is visibly present. For any field you cannot verify on the page, leave it null/omitted — do not invent ID numbers, dates, or names.
- Prefer the schema fields (names, id_number, dates, employer, contract parties) over dumping text into additional_notes."""


def _png_to_data_url(png_bytes: bytes, max_side: int = 1600) -> str:
    """Resize large PNGs to reduce token usage; return data URL for the API."""
    from PIL import Image

    img = Image.open(io.BytesIO(png_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_side:
        ratio = max_side / float(max(w, h))
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def extract_structured_vision(pdf_content: bytes) -> Optional[dict]:
    """
    Render PDF pages to images and call GPT-4o with structured output (VisionPOCExtraction).

    Args:
        pdf_content: Raw PDF bytes

    Returns:
        model_dump dict or None on failure
    """
    if not pdf_content or not settings.openai_api_key:
        logger.warning("Vision extraction skipped: missing PDF or OPENAI_API_KEY")
        return None

    try:
        import fitz  # PyMuPDF
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI

        doc = fitz.open(stream=pdf_content, filetype="pdf")
        try:
            n = min(len(doc), max(1, settings.vision_max_pages))
            dpi = max(72, min(200, settings.vision_render_dpi))
            content: list = [{"type": "text", "text": _VISION_PROMPT}]
            for i in range(n):
                page = doc[i]
                pix = page.get_pixmap(dpi=dpi)
                png_bytes = pix.tobytes("png")
                url = _png_to_data_url(png_bytes)
                content.append({"type": "image_url", "image_url": {"url": url}})
            logger.info("Vision extraction: sending %d page image(s) to %s", n, settings.vision_extraction_model)
        finally:
            doc.close()

        schema = get_extraction_schema("vision_poc")
        llm = ChatOpenAI(
            model=settings.vision_extraction_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )
        structured_llm = llm.with_structured_output(schema)
        msg = HumanMessage(content=content)
        result = structured_llm.invoke([msg])
        if result is None:
            return None
        raw = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        out = strip_empty_extraction_fields(raw)
        logger.info("Vision extraction: %d non-empty fields", len(out))
        return out if out else None
    except Exception as e:
        logger.error("Vision extraction failed: %s", e, exc_info=True)
        return None
