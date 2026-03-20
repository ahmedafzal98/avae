# Task 2.1 — Implementation Plan

**Companies House API Client**

---

## Objective

Create an HTTP client that fetches company data from the Companies House API for verification against extracted document data.

---

## Dependencies

- **Phase 1:** API Registry (1.5), extraction schema (1.3)
- **Config:** `companies_house_api_key` in `.env` (already in config.py)
- **API:** Companies House Public Data API — free, requires registration at https://developer.company-information.service.gov.uk/

---

## Implementation Plan

### Step 1: Create Client Module

**File:** `app/clients/companies_house.py` (new)

**Directory:** Create `app/clients/` if it doesn't exist; add `app/clients/__init__.py`

---

### Step 2: Client Function

**Function:** `fetch_company(company_number: str) -> dict | None`

**Input:** Company number (8 digits, e.g. "00000006" or "12345678")

**Output:** Normalized dict with fields matching CorporateKYCExtraction for verification, or None on failure

**Normalized response structure (for verification):**
```
{
  "company_number": str,
  "company_name": str,
  "registered_office_address": str,  # formatted from address lines
  "company_status": str,
  "company_type": str,
  "incorporation_date": str | None
}
```

**Logic:**
1. Get config via `get_api_config("companies_house")`
2. Build URL: `{base_url}{lookup_path}` with `{id}` replaced by company_number
3. Auth: HTTP Basic with `api_key:` (API key as username, empty password)
4. GET request with `Accept: application/json`
5. Parse response; map API fields to normalized structure
6. Return normalized dict or None on error

---

### Step 3: API Response Mapping

Companies House API returns (GET /company/{number}):
- `company_name`
- `company_status`
- `type` → map to `company_type`
- `date_of_creation` → map to `incorporation_date`
- Registered office address: `GET /company/{number}/registered-office-address` (separate call) or may be in profile

**Approach:** Call main profile first. If registered_office_address is not in profile, call `/company/{number}/registered-office-address` as second request. Format address lines into single string.

---

### Step 4: Error Handling

- **404:** Company not found → return None
- **401:** Invalid API key → log error, return None
- **429:** Rate limit → log, return None (Phase 7 will add retry/backoff)
- **Network/timeout:** catch, log, return None

---

### Step 5: Guard for Missing API Key

At start of `fetch_company`, check `settings.companies_house_api_key`. If None/empty, log warning and return None immediately.

---

## Files to Create

| File | Purpose |
|------|---------|
| `app/clients/__init__.py` | Package init (can export fetch_company) |
| `app/clients/companies_house.py` | Companies House client |

---

## Files to Modify

None. Client is standalone; Task 2.4 will integrate it into the worker.

---

## Verification

| # | Test | Expected |
|---|------|----------|
| 1 | `fetch_company("00000006")` with valid key | Returns dict with company_name, status, etc. |
| 2 | `fetch_company("99999999")` (invalid) | Returns None |
| 3 | Missing COMPANIES_HOUSE_API_KEY | Returns None, logs warning |
| 4 | Invalid API key | Returns None, logs 401 error |

---

## Out of Scope (Task 2.4)

- Worker integration (call after extraction, update audit_logs)
- Verification logic (Task 2.3)
- Rate limiting / retry (Phase 7)

---

## Checklist Before Implementation

- [ ] Plan reviewed and approved
- [ ] Companies House API key obtained and in `.env` as `COMPANIES_HOUSE_API_KEY`

---

**Ready for your approval. Say "start build" to implement.**
