#!/usr/bin/env python3
"""
Batch accuracy test: run AVAE's extraction + verification pipeline directly
(no S3/SQS/upload endpoint) against every PDF in companies_house_test_set/,
and score each document's extracted fields against the ground-truth CSV.

Not part of the app or pipeline — run manually, from document-processor/:

    python scripts/run_accuracy_test.py

How this invokes the pipeline (see also run_mismatch_test.py, which shares
this approach): the compiled LangGraph (app.graph.get_avae_graph) is built for
production use — its entry node (burst_pdf) requires an S3 key, and it ends by
writing to Postgres/Redis via persist()/human_review(), keyed to a real
Document row. None of that applies to a local batch test. Instead, this script
calls the individual node functions from app.graph.nodes directly, in the same
order the graph wires them, stopping after verify() — the last node whose
output we need. This is the same code the production pipeline runs; it's just
invoked as plain functions instead of through the compiled graph.

Cost tracking: app/extraction_service.py's extract_structured() previously
discarded the LLM call's token usage. It now accepts return_usage=True (opt-in,
default-off, so production behavior is unchanged) which switches to
with_structured_output(include_raw=True) and returns usage alongside the
parsed result. app/graph/nodes.py's normalize() passes this through as
extraction_usage in state when state["track_usage"] is set — also opt-in, and
never set by the production entry point (app.graph.run_avae_graph). This
script (and run_mismatch_test.py) are the only callers that set it.
"""
import csv
import logging
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.nodes import (  # noqa: E402
    _burst_pdf_pages,
    classify_pages,
    extract_parallel,
    merge_extractions,
    normalize,
    fetch_api,
    verify,
)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
PDF_DIR = Path(__file__).resolve().parent.parent / "companies_house_test_set"
GROUND_TRUTH_CSV = Path(__file__).resolve().parent.parent / "companies_house_test_set_ground_truth.csv"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_CSV = RESULTS_DIR / "accuracy_test_results.csv"

AUDIT_TARGET = "companies_house"
PIPELINE_NODES = (classify_pages, extract_parallel, merge_extractions, normalize, fetch_api, verify)

# gpt-4o standard API pricing, confirmed against https://developers.openai.com/api/docs/pricing
# on 2026-09-27. Update these if pricing changes.
PRICE_PER_1M_INPUT_TOKENS = 2.50
PRICE_PER_1M_OUTPUT_TOKENS = 10.00

# extracted_json key -> ground-truth CSV column
# Note: the extraction schema (app/schemas_extraction.py) calls this field
# "incorporation_date", not "date_of_creation" — using the latter here silently
# looked up a key that never exists in extracted_json, scoring 0% regardless of
# what was actually extracted. Fixed 2026-09-27.
FIELD_MAP = {
    "company_name": "company_name",
    "company_number": "company_number",
    "company_status": "company_status_api",
    "incorporation_date": "date_of_creation",
}

# Words Companies House uses for company_status. Used to check whether the merged
# extracted document text contains any status word at all, so company_status
# mismatches can be split into "field genuinely absent from this document" vs
# "field was present but extracted wrong" (see summarize_results.py).
STATUS_WORDS = (
    "active", "dissolved", "liquidation", "administration", "receivership",
    "converted-closed", "voluntary arrangement", "insolvency",
)

# Matches common date formats seen in these filings: 2011-11-17, 17/11/2011,
# 27.03.2018, "31 October 2023". Used the same way as STATUS_WORDS above — to
# check whether ANY date appears anywhere in the extracted document text, so
# incorporation_date mismatches can be split into "no date on this document at
# all" vs "a date was there, just not the right one" (see summarize_results.py).
DATE_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b"
    r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    re.IGNORECASE,
)

RESULT_FIELDS = [
    "filename", "company_number", "seconds", "input_tokens", "output_tokens",
    "cost_usd", "verification_status", "error",
    "company_status_verifiable", "incorporation_date_verifiable",
    *[f"{f}_match" for f in FIELD_MAP],
    *[f"{f}_extracted" for f in FIELD_MAP],
    *[f"{f}_ground_truth" for f in FIELD_MAP],
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("accuracy_test")


def _norm(value) -> str:
    return "" if value is None else str(value).strip()


def has_status_word(text: str) -> bool:
    """Whether the merged extracted document text contains any Companies House
    status word — i.e. whether company_status was even verifiable from this
    document, as opposed to architecturally absent from this filing type."""
    lowered = (text or "").lower()
    return any(w in lowered for w in STATUS_WORDS)


def has_date(text: str) -> bool:
    """Whether the merged extracted document text contains any date-like
    pattern at all — i.e. whether incorporation_date was even verifiable from
    this document, as opposed to no date appearing anywhere on the page."""
    return bool(DATE_PATTERN.search(text or ""))


def run_pipeline_local(pdf_path: Path, task_id: str) -> dict:
    """Run classify_pages -> ... -> verify on a local PDF, reusing the exact
    production node functions. Mirrors what burst_pdf would put in state, but
    reads bytes from disk instead of S3 (see _burst_pdf_pages docstring)."""
    pdf_content = pdf_path.read_bytes()
    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp_file.write(pdf_content)
    temp_file.close()

    state = {
        "task_id": task_id,
        "filename": pdf_path.name,
        "audit_target": AUDIT_TARGET,
        "pdf_content": pdf_content,
        "temp_file_path": temp_file.name,
        "pages": _burst_pdf_pages(pdf_content),
        "track_usage": True,
    }
    for node in PIPELINE_NODES:
        state.update(node(state))
    return state


def score_fields(extracted_json: dict | None, ground_truth_row: dict) -> dict:
    row = {}
    extracted_json = extracted_json or {}
    for extracted_key, gt_col in FIELD_MAP.items():
        extracted_val = _norm(extracted_json.get(extracted_key))
        gt_val = _norm(ground_truth_row.get(gt_col))
        row[f"{extracted_key}_match"] = extracted_val != "" and extracted_val.lower() == gt_val.lower()
        row[f"{extracted_key}_extracted"] = extracted_val
        row[f"{extracted_key}_ground_truth"] = gt_val
    return row


def main():
    if not GROUND_TRUTH_CSV.exists():
        log.error(f"Ground truth CSV not found: {GROUND_TRUTH_CSV}")
        sys.exit(1)

    ground_truth = {r["filename"]: r for r in csv.DictReader(GROUND_TRUTH_CSV.open())}
    pdf_files = sorted(p for p in PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        log.error(f"No PDFs found in {PDF_DIR}")
        sys.exit(1)
    log.info(f"Found {len(pdf_files)} PDFs, {len(ground_truth)} ground-truth rows")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    run_start = time.monotonic()

    for i, pdf_path in enumerate(pdf_files, start=1):
        filename = pdf_path.name
        gt_row = ground_truth.get(filename)
        if not gt_row:
            log.warning(f"[{i}/{len(pdf_files)}] {filename}: no ground-truth row, skipping")
            continue

        row = {"filename": filename, "company_number": gt_row.get("company_number", ""), "error": ""}
        t0 = time.monotonic()
        try:
            state = run_pipeline_local(pdf_path, task_id=pdf_path.stem)
            row["seconds"] = round(time.monotonic() - t0, 2)

            usage = state.get("extraction_usage") or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            row["input_tokens"] = input_tokens
            row["output_tokens"] = output_tokens
            row["cost_usd"] = round(
                input_tokens / 1_000_000 * PRICE_PER_1M_INPUT_TOKENS
                + output_tokens / 1_000_000 * PRICE_PER_1M_OUTPUT_TOKENS,
                6,
            )
            row["verification_status"] = state.get("verification_status", "")
            extracted_text = state.get("extracted_text") or ""
            row["company_status_verifiable"] = has_status_word(extracted_text)
            row["incorporation_date_verifiable"] = has_date(extracted_text)
            row.update(score_fields(state.get("extracted_json"), gt_row))
        except Exception as e:
            row["seconds"] = round(time.monotonic() - t0, 2)
            row["error"] = str(e)
            row["input_tokens"] = row["output_tokens"] = row["cost_usd"] = ""
            row["verification_status"] = ""
            row["company_status_verifiable"] = ""
            row["incorporation_date_verifiable"] = ""
            row.update(score_fields(None, gt_row))
            log.error(f"[{i}/{len(pdf_files)}] {filename}: FAILED — {e}")

        results.append(row)
        matches = sum(1 for f in FIELD_MAP if row.get(f"{f}_match"))
        log.info(
            f"[{i}/{len(pdf_files)}] {filename}: {row['seconds']}s, "
            f"{matches}/{len(FIELD_MAP)} fields matched, status={row.get('verification_status', '')}"
        )

    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    elapsed = time.monotonic() - run_start
    errors = [r for r in results if r["error"]]
    print("\n" + "=" * 60)
    print(f"Done: {len(results)} documents processed, {len(errors)} failed")
    print(f"Results written to {RESULTS_CSV}")
    print(f"Total time: {elapsed / 60:.1f} min ({elapsed:.0f}s)")
    if errors:
        print(f"\n{len(errors)} documents failed:")
        for r in errors:
            print(f"  - {r['filename']}: {r['error']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
