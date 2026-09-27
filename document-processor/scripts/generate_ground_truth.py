#!/usr/bin/env python3
"""
One-off utility: generate a ground-truth CSV for the Companies House test-set
PDFs in companies_house_test_set/, for measuring AVAE extraction accuracy.

Not part of the app or pipeline — run manually, from document-processor/:

    python scripts/generate_ground_truth.py

Reuses COMPANIES_HOUSE_API_KEY the same way app/clients/companies_house.py
and scripts/download_test_filings.py do: read from app.config.settings,
HTTP Basic auth with the key as the username and an empty password.
"""
import base64
import csv
import json
import logging
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Make `app` importable when run as `python scripts/generate_ground_truth.py`
# regardless of current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.clients.companies_house import _format_address  # noqa: E402

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
BASE_URL = "https://api.company-information.service.gov.uk"
PDF_DIR = Path(__file__).resolve().parent.parent / "companies_house_test_set"
OUTPUT_CSV = Path(__file__).resolve().parent.parent / "companies_house_test_set_ground_truth.csv"

REQUEST_DELAY_SECONDS = 0.55    # ~109 req/min, comfortably under 600/5min (120/min)
RATE_LIMIT_FALLBACK_WAIT = 60   # used if a 429 has no Retry-After header
MAX_RETRIES = 3

CSV_FIELDS = [
    "filename",
    "company_number",
    "company_name",
    "company_status_api",
    "company_status_filename",
    "status_mismatch",
    "date_of_creation",
    "registered_office_address",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("ch_ground_truth")


# --------------------------------------------------------------------------
# HTTP plumbing: auth, throttling, retry-on-429 (same pattern as download_test_filings.py)
# --------------------------------------------------------------------------
def _auth_header() -> dict:
    api_key = settings.companies_house_api_key
    if not api_key:
        log.error(
            "COMPANIES_HOUSE_API_KEY not set (app.config.settings.companies_house_api_key). "
            "Set it in .env, same as app/clients/companies_house.py expects. Aborting."
        )
        sys.exit(1)
    creds = base64.b64encode(f"{api_key}:".encode()).decode()
    return {"Authorization": f"Basic {creds}"}


_last_request_time = 0.0


def _throttle():
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - elapsed)
    _last_request_time = time.monotonic()


def _get_json(url: str) -> dict | None:
    headers = _auth_header()
    headers["Accept"] = "application/json"

    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        try:
            req = Request(url, headers=headers, method="GET")
            with urlopen(req, timeout=30) as resp:
                body = resp.read()
        except HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", RATE_LIMIT_FALLBACK_WAIT))
                log.warning(f"Rate limited (429) on {url} — waiting {wait}s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            log.warning(f"HTTP {e.code} on {url}: {e.reason}")
            return None
        except URLError as e:
            log.warning(f"Request failed for {url}: {e.reason} (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(2 * attempt)
            continue

        try:
            return json.loads(body.decode())
        except json.JSONDecodeError as e:
            log.warning(f"Bad JSON from {url}: {e}")
            return None

    log.error(f"Giving up on {url} after {MAX_RETRIES} attempts")
    return None


def get_company_profile(company_number: str) -> dict | None:
    return _get_json(f"{BASE_URL}/company/{company_number}")


# --------------------------------------------------------------------------
# Filename parsing
# --------------------------------------------------------------------------
def parse_filename(filename: str) -> tuple[str, str, str]:
    """{company_number}_{status}_{filing_date}.pdf -> (company_number, status, filing_date)."""
    stem = Path(filename).stem
    company_number, status, filing_date = stem.split("_", 2)
    return company_number, status, filing_date


def main():
    start_time = time.monotonic()

    pdf_files = sorted(p.name for p in PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        log.error(f"No PDFs found in {PDF_DIR}")
        sys.exit(1)
    log.info(f"Found {len(pdf_files)} PDFs in {PDF_DIR}")

    profile_cache: dict[str, dict | None] = {}
    failures: list[str] = []
    rows: list[dict] = []
    mismatch_count = 0

    for i, filename in enumerate(pdf_files, start=1):
        company_number, filename_status, _filing_date = parse_filename(filename)

        if company_number not in profile_cache:
            profile = get_company_profile(company_number)
            profile_cache[company_number] = profile
            if profile:
                log.info(f"[{i}/{len(pdf_files)}] Fetched profile for {company_number}")
            else:
                log.warning(f"[{i}/{len(pdf_files)}] Failed to fetch profile for {company_number}")
                failures.append(f"{company_number}: profile fetch failed (see warning above)")
        else:
            log.info(f"[{i}/{len(pdf_files)}] {company_number}: using cached profile")

        profile = profile_cache[company_number]
        if not profile:
            continue  # already logged in failures; no row without ground-truth data

        api_status = profile.get("company_status", "")
        status_mismatch = api_status != filename_status
        if status_mismatch:
            mismatch_count += 1
            log.warning(
                f"{company_number}: status mismatch — filename says '{filename_status}', "
                f"API says '{api_status}'"
            )

        rows.append({
            "filename": filename,
            "company_number": profile.get("company_number", company_number),
            "company_name": profile.get("company_name", ""),
            "company_status_api": api_status,
            "company_status_filename": filename_status,
            "status_mismatch": status_mismatch,
            "date_of_creation": profile.get("date_of_creation", ""),
            "registered_office_address": _format_address(profile.get("registered_office_address")),
        })

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    elapsed = time.monotonic() - start_time

    # --------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"Done: {len(rows)} rows written to {OUTPUT_CSV}")
    print(f"Unique companies looked up: {len(profile_cache)} ({len(profile_cache) - len(failures)} succeeded)")
    print(f"Status mismatches flagged: {mismatch_count}")
    print(f"Time taken: {elapsed / 60:.1f} min ({elapsed:.0f}s)")
    if failures:
        print(f"\n{len(failures)} company lookups failed (rows skipped for their PDFs):")
        for f in failures:
            print(f"  - {f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
