"""
PDF bounding box utilities for verification dashboard.

Finds the location of extracted values within the PDF so the frontend
can highlight them (red for discrepancies, green for verified matches).
Uses PyMuPDF (fitz) for word-level bbox extraction.
"""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_for_search(val: Any) -> str | None:
    """Convert value to searchable string; return None if not searchable."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Normalize whitespace for fuzzy matching
    s = re.sub(r"\s+", " ", s)
    return s


def _normalize_word(w: str) -> str:
    """Strip punctuation for matching (e.g. 'CRN:' -> 'CRN')."""
    return re.sub(r"^[^\w]+|[^\w]+$", "", w)


def find_bbox_for_value(pdf_content: bytes, value: Any) -> dict[str, Any] | None:
    """
    Find the bounding box of a value within a PDF.

    Uses PyMuPDF get_text("words") to get word-level coordinates, then
    searches for the value (exact or fuzzy match) and returns the bbox.

    Returns dict with: page_index (0-based), left, top, width, height (as percentages 0-100).
    react-pdf-viewer HighlightArea expects percentages.
    Returns None if value not found or on error.
    """
    search_str = _normalize_for_search(value)
    if not search_str:
        return None

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_content, filetype="pdf")
        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_rect = page.rect
                page_width = page_rect.width
                page_height = page_rect.height
                if page_width <= 0 or page_height <= 0:
                    continue

                # get_text("words") returns: (x0, y0, x1, y1, word, block_no, line_no, word_no)
                words = page.get_text("words")
                if not words:
                    continue

                # Extract (word_text, bbox) for each word
                word_items: list[tuple[str, tuple[float, float, float, float]]] = []
                for w in words:
                    if len(w) >= 5:
                        x0, y0, x1, y1, word = w[0], w[1], w[2], w[3], w[4]
                        word_items.append((word.strip(), (x0, y0, x1, y1)))

                def _word_matches(tok: str, word: str) -> bool:
                    nw = _normalize_word(word).lower()
                    nt = tok.lower()
                    return nw == nt or (len(nt) >= 1 and nt in nw)

                # Search for token sequence (handles "CRN 0842" as ["CRN", "0842"])
                norm_search = re.sub(r"\s+", " ", search_str)
                tokens = [t for t in norm_search.split() if t]
                if not tokens:
                    continue

                for i in range(len(word_items) - len(tokens) + 1):
                    match = all(
                        _word_matches(tokens[j], word_items[i + j][0])
                        for j in range(len(tokens))
                    )
                    if match:
                        bboxes = [word_items[i + j][1] for j in range(len(tokens))]
                        x0_min = min(b[0] for b in bboxes)
                        y0_min = min(b[1] for b in bboxes)
                        x1_max = max(b[2] for b in bboxes)
                        y1_max = max(b[3] for b in bboxes)
                        left = (x0_min / page_width) * 100
                        top = (y0_min / page_height) * 100
                        width = ((x1_max - x0_min) / page_width) * 100
                        height = ((y1_max - y0_min) / page_height) * 100
                        return {
                            "page_index": page_idx,
                            "left": round(left, 2),
                            "top": round(top, 2),
                            "width": round(width, 2),
                            "height": round(height, 2),
                        }

                # Fallback: single-token search (exact or substring)
                if len(tokens) == 1:
                    tok = tokens[0].lower()
                    for word, (x0, y0, x1, y1) in word_items:
                        nw = _normalize_word(word).lower()
                        if nw == tok or (len(tok) >= 1 and tok in nw):
                            left = (x0 / page_width) * 100
                            top = (y0 / page_height) * 100
                            width = ((x1 - x0) / page_width) * 100
                            height = ((y1 - y0) / page_height) * 100
                            return {
                                "page_index": page_idx,
                                "left": round(left, 2),
                                "top": round(top, 2),
                                "width": round(width, 2),
                                "height": round(height, 2),
                            }

        finally:
            doc.close()

    except Exception as e:
        logger.warning("PDF bbox search failed: %s", e)

    return None
