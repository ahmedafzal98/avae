#!/usr/bin/env python3
"""
Mismatch-detection test: run AVAE's extraction + verification pipeline against
the 20 deliberately-corrupted filings in companies_house_test_set_corrupted/,
and check whether verify() flagged a discrepancy on the SPECIFIC field that
was corrupted (per companies_house_test_set_corrupted_log.csv), not just
whether it flagged something.

Not part of the app or pipeline — run manually, from document-processor/:

    python scripts/run_mismatch_test.py

See run_accuracy_test.py's module docstring for why the pipeline is invoked
as individual node functions (app.graph.nodes) rather than through the
compiled LangGraph — same reasoning applies here unchanged.
"""
import csv
import logging
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
PDF_DIR = Path(__file__).resolve().parent.parent / "companies_house_test_set_corrupted"
CORRUPTION_LOG_CSV = Path(__file__).resolve().parent.parent / "companies_house_test_set_corrupted_log.csv"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_CSV = RESULTS_DIR / "mismatch_test_results.csv"

AUDIT_TARGET = "companies_house"
PIPELINE_NODES = (classify_pages, extract_parallel, merge_extractions, normalize, fetch_api, verify)

PRICE_PER_1M_INPUT_TOKENS = 2.50   # see run_accuracy_test.py for pricing source/date
PRICE_PER_1M_OUTPUT_TOKENS = 10.00

# corruption_log.csv corruption_type -> verify_extraction() discrepancy flag field name
# (app/verification.py's _verify_companies_house uses "company_status", not "status")
CORRUPTION_TO_FLAG_FIELD = {
    "company_number": "company_number",
    "company_name": "company_name",
    "status": "company_status",
}

# app/graph/nodes.py's fetch_api() looks up the Companies House profile using the
# EXTRACTED company_number as the lookup key. So when company_number itself is the
# corrupted field, verify() can never flag it via a direct field-by-field mismatch —
# both sides trivially echo the same (corrupted) number back. The only ways a
# corrupted number gets caught are indirectly: it doesn't match a real company at
# all (fetch_company() 404s -> verify_extraction emits a generic {"field": "api"}
# flag), or it happens to collide with a *different* real company (rare — shows up
# as collateral mismatches on other fields, never on "company_number" itself). Both
# count as a correct catch for this corruption type; neither is a bug in this script.
EXTRA_CATCH_FIELDS_FOR_TYPE = {
    "company_number": {"api"},
}

RESULT_FIELDS = [
    "filename", "corruption_type", "original_value", "corrupted_value",
    "extracted_value_for_field", "api_value_for_field",
    "verification_status", "any_flag_raised", "flagged_correct_field",
    "flagged_fields", "seconds", "input_tokens", "output_tokens", "cost_usd", "error",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("mismatch_test")


def run_pipeline_local(pdf_path: Path, task_id: str) -> dict:
    """Same approach as run_accuracy_test.py — see its docstring for why."""
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


def main():
    if not CORRUPTION_LOG_CSV.exists():
        log.error(f"Corruption log CSV not found: {CORRUPTION_LOG_CSV}")
        sys.exit(1)

    corruption_log = list(csv.DictReader(CORRUPTION_LOG_CSV.open()))
    if not corruption_log:
        log.error(f"Corruption log CSV is empty: {CORRUPTION_LOG_CSV}")
        sys.exit(1)
    log.info(f"Loaded {len(corruption_log)} corrupted-document entries")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    run_start = time.monotonic()

    for i, entry in enumerate(corruption_log, start=1):
        filename = entry["filename"]
        pdf_path = PDF_DIR / filename
        corruption_type = entry["corruption_type"]
        target_field = CORRUPTION_TO_FLAG_FIELD.get(corruption_type)

        row = {
            "filename": filename,
            "corruption_type": corruption_type,
            "original_value": entry["original_value"],
            "corrupted_value": entry["corrupted_value"],
            "error": "",
        }

        if not pdf_path.exists():
            row["error"] = "corrupted PDF not found"
            row["seconds"] = 0
            results.append(row)
            log.warning(f"[{i}/{len(corruption_log)}] {filename}: not found in {PDF_DIR}")
            continue

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

            extracted_json = state.get("extracted_json") or {}
            flags = state.get("discrepancy_flags") or []
            flagged_fields = [f.get("field") for f in flags]

            row["extracted_value_for_field"] = extracted_json.get(target_field, "") if target_field else ""
            row["api_value_for_field"] = (state.get("api_response") or {}).get(target_field, "") if target_field else ""
            row["verification_status"] = state.get("verification_status", "")
            row["any_flag_raised"] = len(flags) > 0
            acceptable_fields = {target_field} | EXTRA_CATCH_FIELDS_FOR_TYPE.get(corruption_type, set())
            row["flagged_correct_field"] = bool(acceptable_fields & set(flagged_fields)) if target_field else False
            row["flagged_fields"] = ";".join(flagged_fields)
        except Exception as e:
            row["seconds"] = round(time.monotonic() - t0, 2)
            row["error"] = str(e)
            row["input_tokens"] = row["output_tokens"] = row["cost_usd"] = ""
            row["extracted_value_for_field"] = row["api_value_for_field"] = ""
            row["verification_status"] = ""
            row["any_flag_raised"] = row["flagged_correct_field"] = False
            row["flagged_fields"] = ""
            log.error(f"[{i}/{len(corruption_log)}] {filename}: FAILED — {e}")

        results.append(row)
        outcome = "CAUGHT" if row["flagged_correct_field"] else ("wrong field" if row["any_flag_raised"] else "MISSED")
        log.info(f"[{i}/{len(corruption_log)}] {filename}: {corruption_type} -> {outcome}")

    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    elapsed = time.monotonic() - run_start
    caught = sum(1 for r in results if r.get("flagged_correct_field"))
    errors = [r for r in results if r["error"]]

    print("\n" + "=" * 60)
    print(f"Done: {len(results)} corrupted documents tested")
    print(f"Correctly flagged the corrupted field: {caught}/{len(results)}")
    print(f"Results written to {RESULTS_CSV}")
    print(f"Total time: {elapsed / 60:.1f} min ({elapsed:.0f}s)")
    if errors:
        print(f"\n{len(errors)} documents failed:")
        for r in errors:
            print(f"  - {r['filename']}: {r['error']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
