"""
AWS Textract extractor for image-only pages (Task 4.3).

OCR for scanned pages and image-heavy content. Uses detect_document_text
for synchronous text extraction from PNG/JPEG bytes.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Max size for Textract bytes: 5 MB
TEXTRACT_MAX_BYTES = 5 * 1024 * 1024


def extract_text_from_image(image_bytes: bytes) -> Optional[str]:
    """
    Extract text from image using AWS Textract OCR.

    Args:
        image_bytes: PNG or JPEG image bytes (max 5 MB)

    Returns:
        Extracted text string, or None on failure
    """
    if not image_bytes or len(image_bytes) == 0:
        logger.warning("Textract: empty image bytes")
        return None

    if len(image_bytes) > TEXTRACT_MAX_BYTES:
        logger.warning(
            "Textract: image too large (%d bytes, max %d), skipping",
            len(image_bytes),
            TEXTRACT_MAX_BYTES,
        )
        return None

    try:
        import boto3
        from app.config import settings

        client = boto3.client(
            "textract",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        response = client.detect_document_text(
            Document={"Bytes": image_bytes}
        )
    except ImportError as e:
        logger.warning("Textract not available: %s", e)
        return None
    except Exception as e:
        logger.error("Textract OCR failed: %s", e)
        return None

    blocks = response.get("Blocks", [])
    lines: list[str] = []
    for block in blocks:
        if block.get("BlockType") == "LINE":
            text = block.get("Text", "")
            if text:
                lines.append(text)

    result = "\n".join(lines) if lines else ""
    logger.debug("Textract extracted %d chars from %d lines", len(result), len(lines))
    return result if result else None
