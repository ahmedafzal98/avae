#!/usr/bin/env python3
"""
One-off utility: download a diverse test-set of Companies House filings (PDFs)
for QA / accuracy-testing of the extraction pipeline.

Not part of the app or pipeline — run manually, from document-processor/:

    python scripts/download_test_filings.py

Reuses COMPANIES_HOUSE_API_KEY the same way app/clients/companies_house.py
does: read from app.config.settings, HTTP Basic auth with the key as the
username and an empty password.
"""
import base64
import json
import logging
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Make `app` importable when run as `python scripts/download_test_filings.py`
# regardless of current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
BASE_URL = "https://api.company-information.service.gov.uk"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "companies_house_test_set"

TARGET_FILINGS = 150
STATUS_BUCKET_RATIOS = {"active": 0.6, "dissolved": 0.2, "other": 0.2}
FILING_CATEGORIES = ("accounts", "confirmation-statement")
MAX_FILINGS_PER_COMPANY = 2

SEARCH_TERMS = [
    "limited", "trading", "services", "holdings",
    "group", "consulting", "properties", "solutions",
]
SEARCH_PAGES_PER_TERM = 3       # 100 results/page -> up to 300 candidates/term
CANDIDATE_POOL_TARGET = 600     # stop gathering search results once pool is this big
MAX_PROFILE_CHECKS = 500        # safety cap on company-profile lookups

REQUEST_DELAY_SECONDS = 0.55    # ~109 req/min, comfortably under 600/5min (120/min)
RATE_LIMIT_FALLBACK_WAIT = 60   # used if a 429 has no Retry-After header
MAX_RETRIES = 3

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("ch_test_set")


def _status_bucket(status: str) -> str:
    if status == "active":
        return "active"
    if status == "dissolved":
        return "dissolved"
    return "other"


# --------------------------------------------------------------------------
# HTTP plumbing: auth, throttling, retry-on-429, redirect-safe download
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


class _StripAuthOnCrossHostRedirect(HTTPRedirectHandler):
    """Companies House document downloads redirect to a pre-signed S3 URL.
    Don't forward our API credentials to that third-party host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and new_req.has_header("Authorization"):
            if urlsplit(req.full_url).netloc != urlsplit(newurl).netloc:
                new_req.remove_header("Authorization")
        return new_req


_opener = build_opener(_StripAuthOnCrossHostRedirect)
_last_request_time = 0.0


def _throttle():
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - elapsed)
    _last_request_time = time.monotonic()


def _request(url: str, accept: str = "application/json") -> bytes | None:
    """GET with auth, rate-limit throttling, and 429/5xx retry. Returns raw body bytes or None."""
    headers = _auth_header()
    headers["Accept"] = accept

    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        try:
            req = Request(url, headers=headers, method="GET")
            with _opener.open(req, timeout=30) as resp:
                return resp.read()
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
    log.error(f"Giving up on {url} after {MAX_RETRIES} attempts")
    return None


def _get_json(url: str) -> dict | None:
    body = _request(url, accept="application/json")
    if body is None:
        return None
    try:
        return json.loads(body.decode())
    except json.JSONDecodeError as e:
        log.warning(f"Bad JSON from {url}: {e}")
        return None


# --------------------------------------------------------------------------
# Companies House API calls
# --------------------------------------------------------------------------
def search_companies(term: str, start_index: int) -> list[dict]:
    qs = urlencode({"q": term, "items_per_page": 100, "start_index": start_index})
    data = _get_json(f"{BASE_URL}/search/companies?{qs}")
    return (data or {}).get("items", [])


def get_company_profile(company_number: str) -> dict | None:
    return _get_json(f"{BASE_URL}/company/{company_number}")


def get_filing_history(company_number: str) -> list[dict]:
    qs = urlencode({"category": list(FILING_CATEGORIES), "items_per_page": 50}, doseq=True)
    data = _get_json(f"{BASE_URL}/company/{company_number}/filing-history?{qs}")
    return (data or {}).get("items", [])


def download_filing_pdf(document_metadata_url: str) -> bytes | None:
    content_url = document_metadata_url.rstrip("/") + "/content"
    return _request(content_url, accept="application/pdf")


# --------------------------------------------------------------------------
# Phase A: gather a diverse pool of candidate company numbers
# --------------------------------------------------------------------------
def gather_candidate_pool() -> list[str]:
    seen: dict[str, None] = {}
    for term in SEARCH_TERMS:
        for page in range(SEARCH_PAGES_PER_TERM):
            items = search_companies(term, start_index=page * 100)
            if not items:
                break
            for item in items:
                number = item.get("company_number")
                if number:
                    seen.setdefault(number, None)
            log.info(f"Search '{term}' page {page + 1}: pool now {len(seen)} unique companies")
            if len(seen) >= CANDIDATE_POOL_TARGET:
                return list(seen.keys())
    return list(seen.keys())


# --------------------------------------------------------------------------
# Phase B: fetch profiles, bucket candidates by status
# --------------------------------------------------------------------------
def bucket_candidates(pool: list[str], companies_needed: dict[str, int]) -> dict[str, list[dict]]:
    random.shuffle(pool)
    buckets: dict[str, list[dict]] = defaultdict(list)
    checked = 0

    for number in pool:
        if checked >= MAX_PROFILE_CHECKS:
            log.warning(f"Hit MAX_PROFILE_CHECKS ({MAX_PROFILE_CHECKS}) while bucketing candidates")
            break
        if all(len(buckets[b]) >= companies_needed[b] for b in companies_needed):
            break

        profile = get_company_profile(number)
        checked += 1
        if not profile:
            continue

        status = profile.get("company_status", "")
        bucket = _status_bucket(status)
        if len(buckets[bucket]) >= companies_needed[bucket]:
            continue  # already have enough of this bucket, skip to keep other buckets moving

        buckets[bucket].append({
            "company_number": profile.get("company_number", number),
            "company_name": profile.get("company_name", ""),
            "status": status,
        })
        log.info(
            f"Checked {checked}: {number} -> {status or 'unknown'} "
            f"[{bucket} bucket: {len(buckets[bucket])}/{companies_needed[bucket]}]"
        )

    return buckets


# --------------------------------------------------------------------------
# Phase C: pick filings per company and download PDFs
# --------------------------------------------------------------------------
def pick_filings(company_number: str) -> list[dict]:
    items = [
        f for f in get_filing_history(company_number)
        if f.get("category") in FILING_CATEGORIES and f.get("links", {}).get("document_metadata")
    ]
    # Prefer one of each category when available, most recent first.
    items.sort(key=lambda f: f.get("date", ""), reverse=True)
    chosen: list[dict] = []
    seen_categories: set[str] = set()
    for f in items:
        if len(chosen) >= MAX_FILINGS_PER_COMPANY:
            break
        if f["category"] not in seen_categories or len(items) <= MAX_FILINGS_PER_COMPANY:
            chosen.append(f)
            seen_categories.add(f["category"])
    if not chosen and items:
        chosen = items[:MAX_FILINGS_PER_COMPANY]
    return chosen


def main():
    start_time = time.monotonic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    companies_needed = {
        bucket: max(1, round((TARGET_FILINGS / 1.5) * ratio * 1.3))  # +30% buffer for companies with no usable filings
        for bucket, ratio in STATUS_BUCKET_RATIOS.items()
    }
    log.info(f"Target: {TARGET_FILINGS} filings, company pool needed per bucket: {companies_needed}")

    log.info("Phase A: searching for a diverse pool of candidate companies...")
    pool = gather_candidate_pool()
    log.info(f"Phase A done: {len(pool)} unique candidate companies found")

    log.info("Phase B: fetching profiles to bucket candidates by status...")
    buckets = bucket_candidates(pool, companies_needed)
    for bucket, needed in companies_needed.items():
        found = len(buckets.get(bucket, []))
        if found < needed:
            log.warning(f"Bucket '{bucket}': only found {found}/{needed} companies via search — mix may skew")

    log.info("Phase C: fetching filing history and downloading PDFs...")
    downloaded = 0
    downloaded_by_status: dict[str, int] = defaultdict(int)
    failures: list[str] = []

    bucket_order = ["active", "dissolved", "other"]
    bucket_targets = {
        b: round(TARGET_FILINGS * STATUS_BUCKET_RATIOS[b]) for b in bucket_order
    }
    bucket_companies = {b: list(buckets.get(b, [])) for b in bucket_order}
    bucket_cursor = {b: 0 for b in bucket_order}

    while downloaded < TARGET_FILINGS:
        progressed = False
        for bucket in bucket_order:
            if downloaded >= TARGET_FILINGS:
                break
            if downloaded_by_status[bucket] >= bucket_targets[bucket]:
                continue
            idx = bucket_cursor[bucket]
            if idx >= len(bucket_companies[bucket]):
                continue
            bucket_cursor[bucket] += 1
            progressed = True

            company = bucket_companies[bucket][idx]
            number, status, name = company["company_number"], company["status"], company["company_name"]

            filings = pick_filings(number)
            if not filings:
                failures.append(f"{number} ({name}): no usable accounts/confirmation-statement filing with a document")
                continue

            for filing in filings:
                if downloaded >= TARGET_FILINGS:
                    break
                date = filing.get("date", "unknown-date")
                doc_url = filing["links"]["document_metadata"]
                pdf_bytes = download_filing_pdf(doc_url)
                if not pdf_bytes:
                    failures.append(f"{number} ({name}) {filing.get('category')} {date}: download failed")
                    continue

                filename = f"{number}_{status or 'unknown'}_{date}.pdf"
                (OUTPUT_DIR / filename).write_bytes(pdf_bytes)
                downloaded += 1
                downloaded_by_status[bucket] += 1
                log.info(f"Downloaded {downloaded}/{TARGET_FILINGS}: {filename}")

        if not progressed:
            break  # exhausted all buckets' companies before hitting target

    elapsed = time.monotonic() - start_time

    # --------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"Done: {downloaded} filings downloaded to {OUTPUT_DIR}")
    print("Breakdown by status bucket:")
    for bucket in bucket_order:
        print(f"  {bucket}: {downloaded_by_status[bucket]}")
    print(f"Time taken: {elapsed / 60:.1f} min ({elapsed:.0f}s)")
    if failures:
        print(f"\n{len(failures)} skipped (see reasons below):")
        for f in failures:
            print(f"  - {f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
