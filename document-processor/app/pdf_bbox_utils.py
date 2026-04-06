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

# Eastern Arabic-Indic digits → Western (for matching OCR vs PDF text layers)
_EASTERN_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _normalize_digits(s: str) -> str:
    return s.translate(_EASTERN_DIGIT_MAP)


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
    """Strip punctuation for matching (e.g. 'CRN:' -> 'CRN'). Keeps Arabic letters."""
    w = _normalize_digits(w.strip())
    return re.sub(r"^[^\w]+|[^\w]+$", "", w, flags=re.UNICODE)


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
                words = page.get_text("words") or []

                # Extract (word_text, bbox) for each word
                word_items: list[tuple[str, tuple[float, float, float, float]]] = []
                for w in words:
                    if len(w) >= 5:
                        x0, y0, x1, y1, word = w[0], w[1], w[2], w[3], w[4]
                        word_items.append((word.strip(), (x0, y0, x1, y1)))

                def _word_matches(tok: str, word: str) -> bool:
                    nw = _normalize_word(word).lower()
                    nt = _normalize_word(tok).lower()
                    return nw == nt or (len(nt) >= 1 and nt in nw)

                def _pct_bbox(x0: float, y0: float, x1: float, y1: float) -> dict[str, Any]:
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

                # Search for token sequence (handles "CRN 0842" as ["CRN", "0842"])
                norm_search = re.sub(r"\s+", " ", search_str)
                tokens = [t for t in norm_search.split() if t]

                if word_items and tokens:
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
                            return _pct_bbox(x0_min, y0_min, x1_max, y1_max)

                    # Fallback: single-token search (exact or substring)
                    if len(tokens) == 1:
                        tok = _normalize_word(tokens[0]).lower()
                        for word, (x0, y0, x1, y1) in word_items:
                            nw = _normalize_word(word).lower()
                            if nw == tok or (len(tok) >= 1 and tok in nw):
                                return _pct_bbox(x0, y0, x1, y1)

                # Substring search in page (helps Arabic phrases and mixed digit forms)
                for variant in (search_str, _normalize_digits(search_str)):
                    if not (variant and variant.strip()):
                        continue
                    try:
                        rects = page.search_for(variant.strip(), quads=False)
                    except Exception as search_err:
                        logger.debug("search_for failed: %s", search_err)
                        rects = []
                    if rects:
                        r = rects[0]
                        return _pct_bbox(r.x0, r.y0, r.x1, r.y1)

        finally:
            doc.close()

    except Exception as e:
        logger.warning("PDF bbox search failed: %s", e)

    return None
