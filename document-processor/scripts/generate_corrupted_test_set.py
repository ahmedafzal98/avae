#!/usr/bin/env python3
"""
One-off utility: create 20 deliberately-corrupted copies of Companies House
test-set filings, to measure AVAE's mismatch-detection rate.

Synthetic QA test data for our own verification pipeline — not real documents,
never distributed outside this test.

Not part of the app or pipeline — run manually, from document-processor/:

    python scripts/generate_corrupted_test_set.py

Step 1 (feasibility) runs automatically at the start of main(): it PyMuPDF-
searches every PDF in companies_house_test_set/ for its own company_number
to confirm a usable text layer exists, and reports how many are usable.
"""
import csv
import itertools
import logging
import random
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

# Make `app` importable for consistency with the other scripts in this folder
# (not actually needed here — this script only reads local files/CSV).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
PDF_DIR = Path(__file__).resolve().parent.parent / "companies_house_test_set"
GROUND_TRUTH_CSV = Path(__file__).resolve().parent.parent / "companies_house_test_set_ground_truth.csv"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "companies_house_test_set_corrupted"
LOG_CSV = Path(__file__).resolve().parent.parent / "companies_house_test_set_corrupted_log.csv"

TARGET_COUNT = 20
CORRUPTION_TYPES = ("company_number", "company_name", "status")
NAME_LABEL = "Company Name:"

LOG_FIELDS = ["filename", "corruption_type", "original_value", "corrupted_value"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("ch_corrupt")


# --------------------------------------------------------------------------
# Step 1: feasibility — does this PDF have an extractable text layer that
# contains its own company_number?
# --------------------------------------------------------------------------
def is_searchable(doc: fitz.Document, company_number: str) -> bool:
    total_chars = sum(len(page.get_text()) for page in doc)
    if total_chars < 50:
        return False
    return any(page.search_for(company_number) for page in doc)


# --------------------------------------------------------------------------
# Locating exact on-page text spans (gives us font size/position for a
# visually-matching overlay, and guarantees we corrupt what's *actually*
# printed rather than assuming the ground-truth CSV value appears verbatim)
# --------------------------------------------------------------------------
def _int_to_rgb(color: int) -> tuple[float, float, float]:
    return ((color >> 16 & 255) / 255, (color >> 8 & 255) / 255, (color & 255) / 255)


def find_exact_text_spans(doc: fitz.Document, text: str) -> list[dict]:
    """All spans (across all pages) whose text is exactly `text`, with page index attached."""
    matches = []
    for page_num, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if span["text"].strip() == text:
                        matches.append({**span, "page_num": page_num})
    return matches


def extract_on_page_company_name(doc: fitz.Document) -> str | None:
    """Pull the name as printed right after a 'Company Name:' label, so we corrupt
    what's literally on the page even if it's drifted from the current API name
    (e.g. the company was renamed since this filing was made)."""
    full_text = "\n".join(page.get_text() for page in doc)
    m = re.search(re.escape(NAME_LABEL) + r"\s*\n\s*(.+)", full_text)
    if not m:
        return None
    return m.group(1).strip()


def has_status_word(doc: fitz.Document) -> bool:
    status_words = (
        "active", "dissolved", "liquidation", "administration", "receivership",
        "converted-closed", "voluntary arrangement", "insolvency",
    )
    text = "\n".join(page.get_text() for page in doc).lower()
    return any(w in text for w in status_words)


def replace_spans(doc: fitz.Document, spans: list[dict], new_text: str) -> int:
    """Redact each span's original text (whiteout) and overlay `new_text` at the
    same position with matching font size/color. Assumes new_text is the same
    length as the original (true for both our corruption types), so it fits
    the original bounding box without wrapping."""
    by_page: dict[int, list[dict]] = {}
    for span in spans:
        by_page.setdefault(span["page_num"], []).append(span)

    for page_num, page_spans in by_page.items():
        page = doc[page_num]
        for span in page_spans:
            page.add_redact_annot(fitz.Rect(span["bbox"]), fill=(1, 1, 1))
        page.apply_redactions()
        for span in page_spans:
            rect = fitz.Rect(span["bbox"])
            baseline = (rect.x0, rect.y1 - span["size"] * 0.15)
            fontname = "hebo" if "Bold" in span.get("font", "") else "helv"
            page.insert_text(
                baseline, new_text,
                fontsize=span["size"], fontname=fontname,
                color=_int_to_rgb(span["color"]),
            )
    return len(spans)


# --------------------------------------------------------------------------
# Corruption value generators
# --------------------------------------------------------------------------
def corrupt_digits(number: str) -> str:
    digits = list(number)
    positions = random.sample(range(len(digits)), k=min(len(digits), random.choice([1, 2])))
    for pos in positions:
        digits[pos] = random.choice([d for d in "0123456789" if d != digits[pos]])
    return "".join(digits)


def corrupt_name_typo(name: str) -> str | None:
    adjacent_letter_pairs = [
        i for i in range(len(name) - 1)
        if name[i].isalpha() and name[i + 1].isalpha() and name[i] != name[i + 1]
    ]
    chars = list(name)
    if adjacent_letter_pairs:
        i = random.choice(adjacent_letter_pairs)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
        return "".join(chars)
    letter_positions = [i for i, c in enumerate(name) if c.isalpha()]
    if not letter_positions:
        return None
    i = random.choice(letter_positions)
    chars[i] = random.choice([c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c != chars[i].upper()])
    return "".join(chars)


# --------------------------------------------------------------------------
# Apply one corruption to one document. Returns a log row dict, or None if
# this corruption type isn't applicable to this document.
# --------------------------------------------------------------------------
def apply_corruption(doc: fitz.Document, corruption_type: str, ground_truth: dict) -> dict | None:
    if corruption_type == "company_number":
        original = ground_truth["company_number"]
        spans = find_exact_text_spans(doc, original)
        if not spans:
            return None
        corrupted = corrupt_digits(original)
        replace_spans(doc, spans, corrupted)
        return {"corruption_type": "company_number", "original_value": original, "corrupted_value": corrupted}

    if corruption_type == "company_name":
        original = extract_on_page_company_name(doc)
        if not original:
            return None
        spans = find_exact_text_spans(doc, original)
        if not spans:
            return None
        corrupted = corrupt_name_typo(original)
        if not corrupted:
            return None
        replace_spans(doc, spans, corrupted)
        return {"corruption_type": "company_name", "original_value": original, "corrupted_value": corrupted}

    if corruption_type == "status":
        if not has_status_word(doc):
            return None
        # Not reached in this corpus (see Step 1 findings in the summary), but
        # implemented for completeness / future filing categories that do print one.
        status_words = {"active": "dissolved", "dissolved": "active", "liquidation": "active"}
        for old, new in status_words.items():
            spans = find_exact_text_spans(doc, old)
            if spans:
                replace_spans(doc, spans, new)
                return {"corruption_type": "status", "original_value": old, "corrupted_value": new}
        return None

    raise ValueError(f"Unknown corruption type: {corruption_type}")


# --------------------------------------------------------------------------
# Step 2: build the searchable candidate pool, bucketed by filename status
# --------------------------------------------------------------------------
def build_candidate_pool(rows: list[dict]) -> tuple[dict[str, list[dict]], list[str]]:
    buckets: dict[str, list[dict]] = {}
    skipped: list[str] = []

    for row in rows:
        path = PDF_DIR / row["filename"]
        try:
            doc = fitz.open(path)
        except Exception as e:
            skipped.append(f"{row['filename']}: could not open PDF ({e})")
            continue
        searchable = is_searchable(doc, row["company_number"])
        doc.close()
        if not searchable:
            skipped.append(f"{row['filename']}: no extractable text layer / company_number not locatable")
            continue
        bucket = row.get("company_status_filename") or row.get("company_status_api") or "other"
        if bucket not in ("active", "dissolved"):
            bucket = "other"
        buckets.setdefault(bucket, []).append(row)

    return buckets, skipped


def select_candidates(buckets: dict[str, list[dict]]) -> list[dict]:
    """Round-robin across status buckets so the pool offered to Step 3 is as
    balanced as availability allows, most-scarce bucket exhausting first."""
    for bucket_rows in buckets.values():
        random.shuffle(bucket_rows)
    order = sorted(buckets.keys(), key=lambda b: len(buckets[b]))  # scarcest first, still gets a fair share
    cursors = {b: 0 for b in order}
    pool: list[dict] = []
    while True:
        progressed = False
        for b in order:
            if cursors[b] < len(buckets[b]):
                pool.append(buckets[b][cursors[b]])
                cursors[b] += 1
                progressed = True
        if not progressed:
            break
    return pool


def main():
    if not GROUND_TRUTH_CSV.exists():
        log.error(f"Ground truth CSV not found: {GROUND_TRUTH_CSV}")
        sys.exit(1)
    rows = list(csv.DictReader(GROUND_TRUTH_CSV.open()))
    log.info(f"Loaded {len(rows)} ground-truth rows")

    log.info("Step 1: checking which PDFs have an extractable, searchable text layer...")
    buckets, unsearchable = build_candidate_pool(rows)
    searchable_total = sum(len(v) for v in buckets.values())
    log.info(
        f"Step 1 done: {searchable_total}/{len(rows)} PDFs are searchable "
        f"({len(unsearchable)} skipped — image-based/scanned, no text layer)"
    )
    for bucket, bucket_rows in sorted(buckets.items()):
        log.info(f"  searchable '{bucket}': {len(bucket_rows)}")

    candidate_pool = select_candidates(buckets)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_rows: list[dict] = []
    type_counts = {t: 0 for t in CORRUPTION_TYPES}
    doc_skips: list[str] = []
    type_cycle = itertools.cycle(CORRUPTION_TYPES)

    log.info("Step 2/3: selecting documents and applying rotating corruptions...")
    for row in candidate_pool:
        if len(log_rows) >= TARGET_COUNT:
            break

        filename = row["filename"]
        attempted_type = next(type_cycle)
        # Try the rotated type first, then fall back through the others so a
        # document that can't take one corruption type (e.g. no status field)
        # still gets used rather than wasted.
        fallback_order = [attempted_type] + [t for t in CORRUPTION_TYPES if t != attempted_type]

        doc = fitz.open(PDF_DIR / filename)
        result = None
        for corruption_type in fallback_order:
            result = apply_corruption(doc, corruption_type, row)
            if result:
                break

        if not result:
            doc.close()
            doc_skips.append(f"{filename}: no corruption type was applicable (no matching text found)")
            log.warning(f"Skipped {filename}: no applicable corruption type found")
            continue

        doc.save(OUTPUT_DIR / filename)
        doc.close()

        type_counts[result["corruption_type"]] += 1
        log_rows.append({"filename": filename, **result})
        log.info(
            f"[{len(log_rows)}/{TARGET_COUNT}] {filename}: {result['corruption_type']} "
            f"'{result['original_value']}' -> '{result['corrupted_value']}'"
        )

    with LOG_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(log_rows)

    # --------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"Done: {len(log_rows)}/{TARGET_COUNT} corrupted documents written to {OUTPUT_DIR}")
    print(f"Corruption log: {LOG_CSV}")
    print("Corruption type breakdown:")
    for t in CORRUPTION_TYPES:
        print(f"  {t}: {type_counts[t]}")
    if type_counts["status"] == 0:
        print(
            "  note: 'status' was never applicable — the accounts/confirmation-statement "
            "filings in this test set don't visibly print a status word on the document "
            "(status is only available via the live API, not the filed PDF itself). "
            "Those rotations fell back to company_number/company_name."
        )
    if unsearchable:
        print(f"\n{len(unsearchable)} PDFs skipped in Step 1 (no usable text layer):")
        for s in unsearchable[:20]:
            print(f"  - {s}")
        if len(unsearchable) > 20:
            print(f"  ... and {len(unsearchable) - 20} more")
    if doc_skips:
        print(f"\n{len(doc_skips)} searchable PDFs skipped in Step 3 (no field matched on page):")
        for s in doc_skips:
            print(f"  - {s}")
    if len(log_rows) < TARGET_COUNT:
        print(
            f"\nWARNING: only reached {len(log_rows)}/{TARGET_COUNT} — the searchable "
            f"candidate pool ({searchable_total} PDFs) was exhausted before hitting target."
        )
    print("=" * 60)


if __name__ == "__main__":
    main()
