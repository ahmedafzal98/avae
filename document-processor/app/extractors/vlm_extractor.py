"""
VLM (Vision Language Model) extractor for chart/graph regions (Task 4.4).

Uses GPT-4 Vision to describe charts, graphs, and visual data.
Produces text summaries for downstream structured extraction.
"""
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Max size for VLM: GPT-4 Vision supports up to 20MB, keep conservative
VLM_MAX_BYTES = 4 * 1024 * 1024  # 4 MB

_CHART_PROMPT = """Describe this chart, graph, or diagram in detail. Extract:
- Chart type (bar, line, pie, etc.)
- Axis labels and units
- Key data points, values, and trends
- Any text labels, legends, or annotations
- Summary of what the visualization shows

Output as plain text suitable for document processing."""


def extract_chart_summary(image_bytes: bytes) -> Optional[str]:
    """
    Extract text summary from chart/graph image using GPT-4 Vision.

    Args:
        image_bytes: PNG or JPEG image bytes (max 4 MB)

    Returns:
        Text summary of the chart, or None on failure
    """
    if not image_bytes or len(image_bytes) == 0:
        logger.warning("VLM: empty image bytes")
        return None

    if len(image_bytes) > VLM_MAX_BYTES:
        logger.warning(
            "VLM: image too large (%d bytes, max %d), skipping",
            len(image_bytes),
            VLM_MAX_BYTES,
        )
        return None

    try:
        from openai import OpenAI

        from app.config import settings

        if not settings.openai_api_key:
            logger.warning("VLM: OPENAI_API_KEY not set")
            return None

        client = OpenAI(api_key=settings.openai_api_key)
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _CHART_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )
        text = response.choices[0].message.content
        if text and text.strip():
            logger.debug("VLM extracted %d chars", len(text))
            return text.strip()
        return None
    except ImportError as e:
        logger.warning("VLM not available: %s", e)
        return None
    except Exception as e:
        logger.error("VLM chart extraction failed: %s", e)
        return None
