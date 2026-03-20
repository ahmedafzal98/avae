# Task 1.3 — Implementation Plan

**Create schema registry (EPCExtraction, CorporateKYC, LandRegistry)**

---

## Objective

Create a central schema registry that defines Pydantic models for structured extraction per audit target. These schemas will be used in Phase 1.4 when the worker extracts compliance entities from document text via an LLM.

---

## Current State

| Component | Status |
|-----------|--------|
| `EPCExtraction` | Exists in `test_document.py` (standalone) |
| `CorporateKYCExtraction` | Not defined |
| `LandRegistryExtraction` | Not defined |
| Schema registry (audit_target → schema) | Not created |
| `api_registry.py` | Has `AuditTarget` enum |

---

## Implementation Plan

### Step 1: Create schemas_extraction.py

**File:** `app/schemas_extraction.py` (new file)

Define three Pydantic models:

---

#### EPCExtraction (UK Energy Performance Certificate)

| Field | Type | Description |
|-------|------|-------------|
| `reference_number` | str | 20-digit RRN (Reference Number) with dashes |
| `property_address` | str | Full address of the property |
| `current_energy_rating` | str | Energy efficiency rating (e.g., 49, 76) |
| `assessor_name` | str | Full name of the energy assessor |
| `assessor_accreditation_number` | str | Assessor accreditation number |
| `total_floor_area` | str | Total floor area with unit (e.g., m2) |

---

#### CorporateKYCExtraction (Companies House)

| Field | Type | Description |
|-------|------|-------------|
| `company_number` | str | 8-digit Companies House registration number |
| `company_name` | str | Registered company name |
| `registered_office_address` | str | Registered office address |
| `company_status` | str | Active, Dissolved, etc. |
| `company_type` | str | ltd, plc, etc. |
| `incorporation_date` | str, optional | Date of incorporation |

---

#### LandRegistryExtraction (HM Land Registry)

| Field | Type | Description |
|-------|------|-------------|
| `title_number` | str | Title number from HM Land Registry |
| `property_address` | str | Property address |
| `tenure` | str | Freehold or Leasehold |
| `proprietor_name` | str, optional | Name of registered proprietor |

---

### Step 2: Create Schema Registry Mapping

**File:** `app/schemas_extraction.py`

Add a mapping from `AuditTarget` to the Pydantic model class:

```python
EXTRACTION_SCHEMA_BY_TARGET = {
    AuditTarget.EPC: EPCExtraction,
    AuditTarget.COMPANIES_HOUSE: CorporateKYCExtraction,
    AuditTarget.HM_LAND_REGISTRY: LandRegistryExtraction,
}
```

---

### Step 3: Add Helper Function

**File:** `app/schemas_extraction.py`

```python
def get_extraction_schema(audit_target: AuditTarget) -> type[BaseModel]:
    """Return the Pydantic extraction schema for the given audit target."""
```

- Input: `AuditTarget` enum or string (normalized)
- Output: The Pydantic model class (e.g., `EPCExtraction`)
- Raises `ValueError` if audit target has no schema

---

### Step 4: Import AuditTarget

**File:** `app/schemas_extraction.py`

Import `AuditTarget` from `app.api_registry` to avoid circular imports and keep a single source of truth.

---

## Files to Create

| File | Action |
|------|--------|
| `app/schemas_extraction.py` | Create |

---

## Files to Modify

None. Task 1.3 is additive only.

---

## Out of Scope (Later Phases)

- **Task 1.4:** Worker will call `get_extraction_schema(audit_target)` and use the schema with an LLM for structured extraction.
- **Task 1.5:** API Registry (base URL, auth) — separate from extraction schemas.

---

## Verification

| # | Check | Command / Action |
|---|-------|------------------|
| 1 | Module imports | `python3 -c "from app.schemas_extraction import EPCExtraction, get_extraction_schema; print(get_extraction_schema('epc'))"` |
| 2 | Schema fields | Instantiate each schema with sample data; validate |
| 3 | Registry mapping | `get_extraction_schema(AuditTarget.EPC)` returns `EPCExtraction` |

---

## Relationship to Other Tasks

| Task | Link |
|------|------|
| 1.1 | `audit_target` flows through system; schema registry uses it to select schema |
| 1.2 | `audit_logs.extracted_json` will store the output of these schemas |
| 1.4 | Worker will use `get_extraction_schema(audit_target)` + LLM to populate `extracted_json` |

---

## Checklist Before Implementation

- [ ] Plan reviewed and approved

---

## Implementation Complete

Task 1.3 has been implemented. Summary:

| File | Changes |
|------|---------|
| `app/schemas_extraction.py` | **Created** — EPCExtraction, CorporateKYCExtraction, LandRegistryExtraction; EXTRACTION_SCHEMA_BY_TARGET; get_extraction_schema() |

**Verify:**
```bash
cd document-processor
python3 -c "from app.schemas_extraction import EPCExtraction, get_extraction_schema; print(get_extraction_schema('epc')); print('OK')"
```
