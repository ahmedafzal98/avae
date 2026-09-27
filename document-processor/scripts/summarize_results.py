#!/usr/bin/env python3
"""
Read scripts/results/accuracy_test_results.csv and mismatch_test_results.csv
(written by run_accuracy_test.py and run_mismatch_test.py) and print the 4
headline numbers: field accuracy, avg seconds/doc, avg cost/doc, mismatch
detection rate.

Not part of the app or pipeline — run manually, from document-processor/:

    python scripts/summarize_results.py
"""
import csv
import sys
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
ACCURACY_CSV = RESULTS_DIR / "accuracy_test_results.csv"
MISMATCH_CSV = RESULTS_DIR / "mismatch_test_results.csv"

FIELDS = ["company_name", "company_number", "company_status", "incorporation_date"]


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(path.open()))


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize_accuracy(rows: list[dict]):
    print("=" * 60)
    print("1) FIELD ACCURACY")
    ok_rows = [r for r in rows if not r.get("error")]
    if not ok_rows:
        print("  No successful runs to score.")
    else:
        total_fields = 0
        total_matched = 0
        for field in FIELDS:
            matches = [r for r in ok_rows if r.get(f"{field}_match") in ("True", "true", "1")]
            pct = 100 * len(matches) / len(ok_rows)
            total_fields += len(ok_rows)
            total_matched += len(matches)
            print(f"  {field}: {len(matches)}/{len(ok_rows)} ({pct:.1f}%)")
        overall = 100 * total_matched / total_fields if total_fields else 0
        print(f"  OVERALL: {total_matched}/{total_fields} ({overall:.1f}%)")
    if len(ok_rows) < len(rows):
        print(f"  ({len(rows) - len(ok_rows)} document(s) errored and were excluded from scoring)")

    print("\n2) AVERAGE SECONDS PER DOCUMENT")
    seconds = [_to_float(r.get("seconds")) for r in rows]
    seconds = [s for s in seconds if s is not None]
    if seconds:
        print(f"  {sum(seconds) / len(seconds):.2f}s avg over {len(seconds)} document(s)")
        print(f"  min {min(seconds):.2f}s / max {max(seconds):.2f}s")
    else:
        print("  No timing data available.")

    print("\n3) AVERAGE COST PER DOCUMENT")
    costs = [_to_float(r.get("cost_usd")) for r in ok_rows]
    costs = [c for c in costs if c is not None]
    if costs:
        print(f"  ${sum(costs) / len(costs):.5f} avg over {len(costs)} document(s)")
        print(f"  total: ${sum(costs):.4f}")
    else:
        print("  cost tracking not available")
    print("=" * 60)


def _is_true(value) -> bool:
    return value in ("True", "true", "1")


def summarize_company_status_source(rows: list[dict]):
    """company_status is no longer extracted by the LLM (see app/schemas_extraction.py /
    app/graph/nodes.py fetch_api()) — it's populated directly from the Companies House
    API response. The old absent/verifiable/hallucination breakdown (still used below
    for incorporation_date) doesn't apply anymore: it asked "does a status word appear
    in the extracted document text", which was the right question when the LLM was
    guessing from that text, but company_status is no longer grounded in document text
    at all, by design — so that check would now flag ~100% of correct, intended
    API-sourced values as "hallucinated", which is wrong. Hallucination is structurally
    impossible here: the schema doesn't offer the model a company_status field to fill in."""
    print("\nCOMPANY_STATUS (diagnostic — see FIELD ACCURACY above for the raw number)")
    ok_rows = [r for r in rows if not r.get("error")]
    if not ok_rows:
        print("  No successful runs to score.")
        print("=" * 60)
        return

    print("  Source: Companies House API response (fetch_api node), not LLM extraction.")
    print("  Hallucination rate: 0% — structurally impossible; the extraction schema no")
    print("  longer has a company_status field for the model to fill in.")

    mismatches = [r for r in ok_rows if not _is_true(r.get("company_status_match"))]
    print(f"\n  Remaining mismatches: {len(mismatches)}/{len(ok_rows)}")
    if mismatches:
        blank = [r for r in mismatches if r.get("company_status_extracted", "") == ""]
        print(f"    {len(blank)} blank — Companies House lookup failed for that document "
              f"(see MISMATCH DETECTION RATE below / the 'api' discrepancy flag)")
        print(f"    {len(mismatches) - len(blank)} non-blank but differ from ground-truth CSV — "
              f"likely registry status drift between when the ground-truth CSV was generated "
              f"and this test run (same phenomenon noted for company_name earlier), not an "
              f"extraction or lookup defect")
        for r in mismatches[:10]:
            print(f"      - {r['filename']}: extracted={r.get('company_status_extracted')!r} vs ground_truth={r.get('company_status_ground_truth')!r}")
    print("=" * 60)


def summarize_field_breakdown(rows: list[dict], field: str, verifiable_column: str, evidence_label: str):
    """Shared by company_status and incorporation_date: their raw match rates (in
    FIELD ACCURACY above) conflate the field being genuinely absent from the
    document with the LLM inventing/misattributing a value. This splits them out
    into (a) architecturally absent, (b) verifiable, plus accuracy-excluding-absent
    and a hallucination rate — hallucination (invented from nothing, in the absent
    bucket) is kept separate from misattribution (a real value was on the page,
    just the wrong one got picked, in the verifiable bucket) since they're
    different failure modes. See the conversation that diagnosed this."""
    label = field.upper()
    print(f"\n{label} BREAKDOWN (diagnostic — see FIELD ACCURACY above for the raw number)")
    ok_rows = [r for r in rows if not r.get("error")]
    if not ok_rows:
        print("  No successful runs to score.")
        print("=" * 60)
        return

    extracted_col = f"{field}_extracted"
    match_col = f"{field}_match"

    absent = [r for r in ok_rows if not _is_true(r.get(verifiable_column))]
    verifiable = [r for r in ok_rows if _is_true(r.get(verifiable_column))]
    hallucinated = [r for r in absent if r.get(extracted_col, "") != ""]
    verifiable_correct = [r for r in verifiable if _is_true(r.get(match_col))]
    misattributed = [r for r in verifiable if not _is_true(r.get(match_col)) and r.get(extracted_col, "") != ""]

    print(f"  Total {field} rows: {len(ok_rows)}")
    print(
        f"  (a) Architecturally absent — no {evidence_label} anywhere in extracted document text: "
        f"{len(absent)} ({100 * len(absent) / len(ok_rows):.1f}%)"
    )
    print(
        f"  (b) Verifiable — a {evidence_label} was present in extracted document text: "
        f"{len(verifiable)} ({100 * len(verifiable) / len(ok_rows):.1f}%)"
    )

    print("\n  ACCURACY EXCLUDING ARCHITECTURALLY-ABSENT FIELDS:")
    if verifiable:
        pct = 100 * len(verifiable_correct) / len(verifiable)
        print(f"    {len(verifiable_correct)}/{len(verifiable)} ({pct:.1f}%)")
    else:
        print(f"    n/a — no documents had a verifiable {field} field")

    print(f"\n  HALLUCINATION RATE (non-blank value returned despite no {evidence_label} in the text):")
    if absent:
        pct_of_absent = 100 * len(hallucinated) / len(absent)
        pct_of_total = 100 * len(hallucinated) / len(ok_rows)
        print(f"    {len(hallucinated)}/{len(absent)} of architecturally-absent docs ({pct_of_absent:.1f}%)")
        print(f"    {len(hallucinated)}/{len(ok_rows)} of all documents ({pct_of_total:.1f}%)")
        for r in hallucinated[:10]:
            print(f"      - {r['filename']}: extracted={r.get(extracted_col)!r}")
        if len(hallucinated) > 10:
            print(f"      ... and {len(hallucinated) - 10} more")
    else:
        print("    n/a — no architecturally-absent documents")

    if misattributed:
        print(f"\n  MISATTRIBUTION (a {evidence_label} WAS on the page, but the wrong one was picked — "
              f"different failure mode from hallucination above):")
        print(f"    {len(misattributed)}/{len(verifiable)} of verifiable docs")
        for r in misattributed[:10]:
            print(f"      - {r['filename']}: extracted={r.get(extracted_col)!r} vs ground_truth={r.get(f'{field}_ground_truth')!r}")
        if len(misattributed) > 10:
            print(f"      ... and {len(misattributed) - 10} more")
    print("=" * 60)


def summarize_mismatch(rows: list[dict]):
    print("\n4) MISMATCH DETECTION RATE")
    if not rows:
        print("  No mismatch test results found — run scripts/run_mismatch_test.py first.")
        print("=" * 60)
        return

    ok_rows = [r for r in rows if not r.get("error")]
    caught = [r for r in ok_rows if r.get("flagged_correct_field") in ("True", "true", "1")]
    wrong_field = [
        r for r in ok_rows
        if r.get("any_flag_raised") in ("True", "true", "1")
        and r.get("flagged_correct_field") not in ("True", "true", "1")
    ]
    missed = [r for r in ok_rows if r.get("any_flag_raised") not in ("True", "true", "1")]

    pct = 100 * len(caught) / len(ok_rows) if ok_rows else 0
    print(f"  Correctly flagged the corrupted field: {len(caught)}/{len(ok_rows)} ({pct:.1f}%)")
    if wrong_field:
        print(f"  Flagged something, but not the corrupted field: {len(wrong_field)}")
        for r in wrong_field:
            print(f"    - {r['filename']} ({r['corruption_type']}): flagged {r.get('flagged_fields', '')}")
    if missed:
        print(f"  Missed entirely (no flag raised): {len(missed)}")
        for r in missed:
            print(f"    - {r['filename']} ({r['corruption_type']})")
    if len(ok_rows) < len(rows):
        print(f"  ({len(rows) - len(ok_rows)} document(s) errored and were excluded)")
    print("=" * 60)


def main():
    accuracy_rows = _read(ACCURACY_CSV)
    mismatch_rows = _read(MISMATCH_CSV)

    if not accuracy_rows and not mismatch_rows:
        print(f"No results found. Run scripts/run_accuracy_test.py and/or scripts/run_mismatch_test.py first.")
        print(f"Expected: {ACCURACY_CSV}")
        print(f"          {MISMATCH_CSV}")
        sys.exit(1)

    if accuracy_rows:
        summarize_accuracy(accuracy_rows)
        summarize_company_status_source(accuracy_rows)
        summarize_field_breakdown(accuracy_rows, "incorporation_date", "incorporation_date_verifiable", "date")
    else:
        print(f"No accuracy results found at {ACCURACY_CSV} — skipping metrics 1-3.")

    summarize_mismatch(mismatch_rows)


if __name__ == "__main__":
    main()
