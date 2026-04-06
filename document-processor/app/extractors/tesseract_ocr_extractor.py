"""
Tesseract OCR for image-based PDF pages (Arabic + English).

Used before AWS Textract for page types classified as scanned/image: Textract does not
support Arabic printed text. Requires system `tesseract` with Arabic traineddata (`ara`).
"""
import io
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def extract_text_from_image_tesseract(image_bytes: bytes) -> Optional[str]:
    """
    OCR image bytes using Tesseract (Arabic + English by default).

    Returns:
        Extracted text, or None if disabled, unavailable, or empty.
    """
    if not image_bytes or not getattr(settings, "tesseract_enabled", True):
        return None

    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.debug("pytesseract not installed; skipping Tesseract OCR")
        return None

    cmd = getattr(settings, "tesseract_cmd", None)
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

    lang = (getattr(settings, "tesseract_lang", None) or "ara+eng").strip()

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        text = pytesseract.image_to_string(img, lang=lang)
        text = (text or "").strip()
        if text:
            logger.debug("Tesseract OCR: %d chars (lang=%s)", len(text), lang)
            return text
    except Exception as e:
        err = str(e).lower()
        if "tesseract" in err and ("not installed" in err or "not found" in err or "failed loading language" in err):
            logger.warning(
                "Tesseract OCR unavailable (%s). Install the binary and language packs (e.g. "
                "brew install tesseract tesseract-lang; or apt install tesseract-ocr tesseract-ocr-ara).",
                e,
            )
        else:
            logger.warning("Tesseract OCR failed: %s", e)

    return None
