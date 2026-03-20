# Financial & Stock Market Vertical — Integration Guide

**AVAE: Agentic Verification and Audit Engine**

This guide provides a step-by-step technical plan to integrate the Financial sector (stock market, corporate finance documents) into the existing AVAE architecture. The workflow mirrors Companies House and HM Land Registry: user selects "Financial" from the dropdown, uploads a document (e.g., quarterly earnings report), the system extracts data, cross-references with the SEC EDGAR API, and flags matched values and discrepancies for human review.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Phase 1: Backend Core — Audit Target & API Registry](#3-phase-1-backend-core--audit-target--api-registry)
4. [Phase 2: SEC EDGAR Client](#4-phase-2-sec-edgar-client)
5. [Phase 3: Extraction Schema & Verification Logic](#5-phase-3-extraction-schema--verification-logic)
6. [Phase 4: Pipeline Integration](#6-phase-4-pipeline-integration)
7. [Phase 5: Frontend](#7-phase-5-frontend)
8. [Phase 6: Configuration & Testing](#8-phase-6-configuration--testing)
9. [Implementation Checklist](#9-implementation-checklist)

---

## 1. Overview

### Architecture Alignment

| Component | Companies House | HM Land Registry | Financial (New) |
|-----------|-----------------|------------------|-----------------|
| **Audit Target** | `companies_house` | `hm_land_registry` | `financial` |
| **Lookup Key** | `company_number` | `property_address` | `cik` (Central Index Key) |
| **API** | Companies House API | Land Registry SPARQL | SEC EDGAR (data.sec.gov) |
| **Auth** | API key | None | None (User-Agent required) |
| **Schema** | CorporateKYCExtraction | LandRegistryExtraction | FinancialExtraction |

### Document Types Supported (Phase 1)

- **10-K / 10-Q** — Annual and quarterly financial statements
- **8-K** — Material event announcements
- **Earnings reports** — PDFs containing revenue, net income, EPS, etc.

### SEC EDGAR API (Free, No Auth)

| Endpoint | Purpose |
|----------|---------|
| `https://data.sec.gov/submissions/CIK{cik}.json` | Company metadata, filing history |
| `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json` | All XBRL financial concepts |
| `https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json` | Single concept (e.g., Revenue) |

**Rate limit:** 10 requests/second. **User-Agent required** (identify your app).

---

## 2. Prerequisites

- [ ] Python 3.11+ in `document-processor`
- [ ] Existing AVAE pipeline working (upload → extract → verify → HITL)
- [ ] `OPENAI_API_KEY` for structured extraction
- [ ] `LLAMA_CLOUD_API_KEY` for table extraction (financial docs have tables)
- [ ] No SEC API key needed; User-Agent header is required

---

## 3. Phase 1: Backend Core — Audit Target & API Registry

### Step 1.1: Add `FINANCIAL` to AuditTarget enum

**File:** `document-processor/app/api_registry.py`

```python
class AuditTarget(str, Enum):
    """Supported audit targets for compliance verification."""
    COMPANIES_HOUSE = "companies_house"
    HM_LAND_REGISTRY = "hm_land_registry"
    EPC = "epc"
    FINANCIAL = "financial"  # ADD THIS
```

### Step 1.2: Add API config for SEC EDGAR

**File:** `document-processor/app/api_registry.py`

Add to `AUDIT_TARGET_CONFIG`:

```python
AuditTarget.FINANCIAL: APIConfig(
    base_url="https://data.sec.gov",
    id_field="cik",
    lookup_path="/api/xbrl/companyfacts/CIK{id}.json",
    auth_type="none",
    auth_env_vars=(),
    rate_limit_per_min=600,  # 10/sec = 600/min
),
```

**Note:** `lookup_path` uses `{id}` placeholder. The SEC uses CIK (10-digit, zero-padded). The `id_field` is `cik` from the extraction schema.

---

## 4. Phase 2: SEC EDGAR Client

### Step 2.1: Create SEC EDGAR client module

**File:** `document-processor/app/clients/sec_edgar.py` (new)

```python
"""
SEC EDGAR API client for AVAE financial verification.

Fetches company facts (XBRL) from data.sec.gov. No API key required.
User-Agent header is required per SEC policy.
"""
import json
import logging
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

# SEC requires User-Agent identifying the application
USER_AGENT = "AVAE Document Processor (compliance verification; contact@example.com)"


def _normalize_cik(cik: str) -> str:
    """Ensure CIK is 10-digit zero-padded."""
    if not cik:
        return ""
    digits = "".join(c for c in str(cik) if c.isdigit())
    return digits.zfill(10) if digits else ""


def fetch_company_facts(cik: str) -> dict | None:
    """
    Fetch XBRL company facts from SEC EDGAR.

    Args:
        cik: 10-digit Central Index Key (or ticker; caller should resolve to CIK first)

    Returns:
        Normalized dict with company_name, cik, and financial metrics for verification;
        or None on failure
    """
    cik = _normalize_cik(cik)
    if not cik or len(cik) != 10:
        logger.warning("SEC EDGAR: invalid or empty CIK")
        return None

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 404:
            logger.info(f"SEC EDGAR: CIK {cik} not found")
        elif e.code == 429:
            logger.warning("SEC EDGAR: rate limit exceeded")
        else:
            logger.error(f"SEC EDGAR HTTP error {e.code}: {e.reason}")
        return None
    except (URLError, json.JSONDecodeError, TimeoutError) as e:
        logger.error(f"SEC EDGAR request failed: {e}")
        return None

    # Extract entity name
    entity = data.get("entityName", "")
    facts = data.get("facts", {}).get("us-gaap", {})

    # Build normalized structure for verification
    # Map common XBRL concepts to our schema fields
    result: dict[str, Any] = {
        "cik": cik,
        "company_name": entity,
        "revenue": None,
        "net_income": None,
        "total_assets": None,
        "eps_diluted": None,
    }

    def _latest_usd(concept_key: str) -> Any:
        """Get latest USD value for a us-gaap concept."""
        concept = facts.get(concept_key, {})
        units = concept.get("units", {}).get("USD", [])
        if not units:
            return None
        # Prefer 10-K/10-Q over other forms; take most recent
        sorted_units = sorted(units, key=lambda x: (x.get("form", ""), x.get("end", "") or ""), reverse=True)
        return sorted_units[0].get("val") if sorted_units else None

    result["revenue"] = _latest_usd("Revenues") or _latest_usd("RevenueFromContractWithCustomerExcludingAssessedTax")
    result["net_income"] = _latest_usd("NetIncomeLoss")
    result["total_assets"] = _latest_usd("Assets")
    result["eps_diluted"] = _latest_usd("EarningsPerShareDiluted")

    return result
```

### Step 2.2: Export from clients package

**File:** `document-processor/app/clients/__init__.py`

Add:

```python
from app.clients.sec_edgar import fetch_company_facts
# In __all__ or ensure it's importable where needed
```

---

## 5. Phase 3: Extraction Schema & Verification Logic

### Step 3.1: Add FinancialExtraction schema

**File:** `document-processor/app/schemas_extraction.py`

```python
# ---------------------------------------------------------------------------
# Financial — SEC EDGAR (10-K, 10-Q, earnings reports)
# ---------------------------------------------------------------------------

class FinancialExtraction(BaseModel):
    """Structured extraction for financial documents (SEC EDGAR verification)."""
    cik: str = Field(description="The 10-digit Central Index Key (CIK) of the company.")
    company_name: str = Field(description="The company or issuer name.")
    filing_type: Optional[str] = Field(default=None, description="10-K, 10-Q, 8-K, or similar.")
    period_end_date: Optional[str] = Field(default=None, description="Fiscal period end date (YYYY-MM-DD or similar).")
    revenue: Optional[str] = Field(default=None, description="Total revenue for the period.")
    net_income: Optional[str] = Field(default=None, description="Net income (loss) for the period.")
    total_assets: Optional[str] = Field(default=None, description="Total assets.")
    eps_diluted: Optional[str] = Field(default=None, description="Diluted earnings per share.")
```

Add to `EXTRACTION_SCHEMA_BY_TARGET`:

```python
EXTRACTION_SCHEMA_BY_TARGET = {
    AuditTarget.EPC: EPCExtraction,
    AuditTarget.COMPANIES_HOUSE: CorporateKYCExtraction,
    AuditTarget.HM_LAND_REGISTRY: LandRegistryExtraction,
    AuditTarget.FINANCIAL: FinancialExtraction,  # ADD THIS
}
```

### Step 3.2: Add financial verification function

**File:** `document-processor/app/verification.py`

Add helper for numeric comparison (financial values need tolerance):

```python
def _normalize_numeric(value: Any) -> str:
    """Normalize numeric string for comparison: strip, remove commas, keep digits and decimal."""
    if value is None:
        return ""
    s = str(value).strip().replace(",", "").replace(" ", "")
    # Keep digits, decimal point, minus
    return "".join(c for c in s if c.isdigit() or c in ".-")
```

Add `_verify_financial`:

```python
def _verify_financial(
    extracted: dict[str, Any], api: dict[str, Any]
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Verify financial extraction against SEC EDGAR company facts."""
    fields = ["cik", "company_name", "revenue", "net_income", "total_assets", "eps_diluted"]
    flags: list[dict[str, Any]] = []
    compared: list[str] = []

    for field in fields:
        ext_val = extracted.get(field)
        api_val = api.get(field)
        compared.append(field)

        if ext_val is None and api_val is None:
            continue
        if ext_val is None and api_val:
            continue
        if api_val is None and ext_val:
            flags.append({"field": field, "extracted": ext_val, "api": None})
            continue

        if field == "cik":
            a = "".join(c for c in str(ext_val) if c.isdigit()).zfill(10)
            b = "".join(c for c in str(api_val) if c.isdigit()).zfill(10)
            match = a == b
        elif field == "company_name":
            match = _values_match(ext_val, api_val)
        else:
            # Numeric: compare within 1% tolerance for rounding
            a = _normalize_numeric(ext_val)
            b = _normalize_numeric(api_val)
            if not a or not b:
                match = a == b
            else:
                try:
                    va, vb = float(a), float(b)
                    match = abs(va - vb) / max(abs(vb), 1e-10) <= 0.01
                except ValueError:
                    match = a == b

        if not match:
            flags.append({"field": field, "extracted": ext_val, "api": api_val})

    status = VERIFIED if not flags else DISCREPANCY_FLAG
    return status, flags, compared
```

Add branch in `verify_extraction`:

```python
elif audit_target == AuditTarget.FINANCIAL:
    status, flags, compared = _verify_financial(extracted_json, api_response_json)
```

---

## 6. Phase 4: Pipeline Integration

### Step 4.1: Add financial branch in fetch_api

**File:** `document-processor/app/graph/nodes.py`

In `fetch_api`:

```python
elif audit_target == "financial":
    from app.clients.sec_edgar import fetch_company_facts
    cik = extracted_json.get("cik", "")
    api_response = fetch_company_facts(cik)
```

### Step 4.2: Update extraction_service prompt (optional)

**File:** `document-processor/app/extraction_service.py`

The generic prompt works for financial docs. Optionally add a hint for financial:

```python
# In extract_structured, before building prompt:
if audit_target == "financial":
    prompt = (
        "Extract financial and corporate data from this document (10-K, 10-Q, earnings report, etc.). "
        "Include CIK (10-digit), company name, filing type, period, revenue, net income, total assets, EPS. "
        "Return only the structured fields, no additional commentary.\n\n"
        "Document text:\n---\n{text}\n---"
    ).format(text=truncated)
else:
    prompt = (
        "Extract the compliance entities from this document. "
        "Return only the structured fields, no additional commentary.\n\n"
        "Document text:\n---\n{text}\n---"
    ).format(text=truncated)
```

### Step 4.3: Update schema validation in main.py / schemas_api

**File:** `document-processor/app/schemas_api.py`

Update any `audit_target` description from:

```
epc | companies_house | hm_land_registry
```

to:

```
epc | companies_house | hm_land_registry | financial
```

**File:** `document-processor/app/main.py`

The `validate_audit_target` from `api_registry` will automatically include `financial` once added to the enum. No change needed if you use `get_valid_audit_targets()`.

### Step 4.4: Update HITL and audit schemas

**File:** `document-processor/app/schemas_hitl.py`

Update `audit_target` Field description to include `financial`.

**File:** `document-processor/app/audit_service.py`  
**File:** `document-processor/app/hitl_service.py`

No code changes required; they filter by `audit_target` string, so `"financial"` will work once validated.

---

## 7. Phase 5: Frontend

### Step 5.1: Add Financial to audit target type

**File:** `frontend/src/types/audit-target.ts`

```typescript
export type AuditTarget = "epc" | "companies_house" | "hm_land_registry" | "financial";

export const AUDIT_TARGETS: { value: AuditTarget; label: string }[] = [
  { value: "epc", label: "EPC (Energy Performance Certificate)" },
  { value: "companies_house", label: "Companies House" },
  { value: "hm_land_registry", label: "HM Land Registry" },
  { value: "financial", label: "Financial (SEC / Stock Market)" },
];
```

### Step 5.2: Update formatAuditTarget (if used)

**File:** `frontend/src/components/audit/AuditLogTable.tsx`

In `formatAuditTarget`, add:

```typescript
case "financial":
  return "Financial (SEC)";
```

(Or similar display label.)

---

## 8. Phase 6: Configuration & Testing

### Step 6.1: Environment variables

**File:** `document-processor/.env`

No new env vars for SEC EDGAR (no auth). Optional: customize User-Agent in `sec_edgar.py` if SEC requests it.

### Step 6.2: Database migration (if needed)

If `audit_target` column has a CHECK constraint limiting values, add a migration:

**File:** `document-processor/migrations/00X_add_financial_audit_target.sql` (if applicable)

```sql
-- Only if you have a CHECK constraint on audit_target
-- ALTER TABLE documents DROP CONSTRAINT IF EXISTS ...;
-- ALTER TABLE documents ADD CONSTRAINT ... CHECK (audit_target IN ('epc','companies_house','hm_land_registry','financial'));
```

Most setups use `VARCHAR(50)` without CHECK; `"financial"` will work as-is.

### Step 6.3: Manual test flow

1. **Upload:** `POST /upload?user_id=1&audit_target=financial` with a 10-K or earnings PDF.
2. **Worker:** Ensure SQS worker processes with `audit_target=financial`.
3. **Extraction:** Check `audit_logs.extracted_json` for `cik`, `company_name`, `revenue`, etc.
4. **API:** Verify `api_response_json` contains SEC data.
5. **Verification:** Check `verification_status` is VERIFIED or DISCREPANCY_FLAG.
6. **Frontend:** Select "Financial (SEC / Stock Market)" in dropdown, upload, view verification dashboard.

### Step 6.4: Unit tests

**File:** `document-processor/tests/test_verification.py`

Add:

```python
def test_financial_verified():
    extracted = {"cik": "320193", "company_name": "Apple Inc.", "revenue": "383285000000", "net_income": "96995000000"}
    api = {"cik": "320193", "company_name": "Apple Inc.", "revenue": 383285000000, "net_income": 96995000000}
    result = verify_extraction("financial", extracted, api)
    assert result.status == "VERIFIED"

def test_financial_discrepancy():
    extracted = {"cik": "320193", "revenue": "400000000000"}
    api = {"cik": "320193", "revenue": 383285000000}
    result = verify_extraction("financial", extracted, api)
    assert result.status == "DISCREPANCY_FLAG"
```

---

## 9. Implementation Checklist

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1 | Add `FINANCIAL` to AuditTarget enum | `api_registry.py` | |
| 2 | Add SEC EDGAR APIConfig | `api_registry.py` | |
| 3 | Create `sec_edgar.py` client | `app/clients/sec_edgar.py` | |
| 4 | Export `fetch_company_facts` | `app/clients/__init__.py` | |
| 5 | Add FinancialExtraction schema | `schemas_extraction.py` | |
| 6 | Add `_verify_financial` and `_normalize_numeric` | `verification.py` | |
| 7 | Add financial branch in `verify_extraction` | `verification.py` | |
| 8 | Add financial branch in `fetch_api` | `graph/nodes.py` | |
| 9 | Update schema descriptions | `schemas_api.py`, `schemas_hitl.py` | |
| 10 | Add Financial to frontend type & AUDIT_TARGETS | `types/audit-target.ts` | |
| 11 | Update formatAuditTarget | `AuditLogTable.tsx` | |
| 12 | Add unit tests | `tests/test_verification.py` | |
| 13 | Manual end-to-end test | — | |

---

## 10. Future Enhancements (Out of Scope for Phase 1)

- **Ticker → CIK lookup:** SEC provides `company_tickers.json`; add resolver if users upload by ticker.
- **8-K / material announcements:** Different schema (event type, date); separate sub-type or schema.
- **Form 4 (insider trading):** Requires different API or parsing; Phase 2.
- **UK financial (FCA, RNS):** Separate audit target if needed.

---

## 11. File Change Summary

| File | Change |
|------|--------|
| `app/api_registry.py` | +FINANCIAL enum, +APIConfig |
| `app/clients/sec_edgar.py` | New file |
| `app/clients/__init__.py` | +import fetch_company_facts |
| `app/schemas_extraction.py` | +FinancialExtraction, +registry entry |
| `app/verification.py` | +_normalize_numeric, +_verify_financial, +branch |
| `app/graph/nodes.py` | +financial branch in fetch_api |
| `app/extraction_service.py` | Optional prompt tweak |
| `app/schemas_api.py` | Update audit_target description |
| `app/schemas_hitl.py` | Update audit_target description |
| `frontend/src/types/audit-target.ts` | +financial type and option |
| `frontend/src/components/audit/AuditLogTable.tsx` | +formatAuditTarget case |
| `tests/test_verification.py` | +test_financial_* |

---

**End of guide.** Follow phases in order; each phase builds on the previous.
