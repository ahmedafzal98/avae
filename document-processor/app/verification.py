"""
AVAE verification module — deterministic comparison of extracted data vs API response.

Compares extracted_json (from LLM) against api_response_json (from external API)
and returns VERIFIED or DISCREPANCY_FLAG with discrepancy details.

No LLM; purely rule-based comparison with normalization.
"""
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.api_registry import AuditTarget

logger = logging.getLogger(__name__)

VERIFIED = "VERIFIED"
DISCREPANCY_FLAG = "DISCREPANCY_FLAG"
# Extraction succeeded but no external verification source available (e.g. non-US financial docs)
EXTRACTED = "EXTRACTED"


@dataclass
class VerificationResult:
    """Result of verify_extraction()."""

    status: str  # VERIFIED or DISCREPANCY_FLAG
    discrepancy_flags: list[dict[str, Any]]
    fields_compared: list[str]


def _normalize(value: Any) -> str:
    """Normalize value for comparison: strip, lowercase, collapse whitespace."""
    if value is None:
        return ""
    s = str(value).strip()
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def _normalize_address(addr: str) -> str:
    """Normalize address: strip, lowercase, collapse whitespace and commas."""
    if not addr or not isinstance(addr, str):
        return ""
    s = addr.strip().lower()
    s = re.sub(r"[\s,]+", " ", s)
    return s


# UK postcode pattern for Land Registry address matching
_UK_POSTCODE = re.compile(r"\b([A-Z]{1,2}[0-9][0-9A-Z]?)\s*([0-9][A-Z]{2})\b", re.IGNORECASE)


def _extract_postcode(addr: str) -> str | None:
    """Extract UK postcode from address. Returns normalized postcode or None."""
    if not addr or not isinstance(addr, str):
        return None
    m = _UK_POSTCODE.search(addr.strip())
    return f"{m.group(1).upper()} {m.group(2).upper()}" if m else None


def _values_match(extracted: Any, api_val: Any, normalize_fn=None) -> bool:
    """Compare two values; optionally use custom normalizer."""
    fn = normalize_fn or _normalize
    a = fn(extracted) if extracted is not None else ""
    b = fn(api_val) if api_val is not None else ""
    return a == b


def _verify_companies_house(
    extracted: dict[str, Any], api: dict[str, Any]
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Verify Companies House extraction against API response."""
    fields = [
        "company_number",
        "company_name",
        "registered_office_address",
        "company_status",
        "company_type",
        "incorporation_date",
    ]
    flags: list[dict[str, Any]] = []
    compared: list[str] = []

    for field in fields:
        ext_val = extracted.get(field)
        api_val = api.get(field)
        compared.append(field)

        if ext_val is None and api_val is None:
            continue
        if ext_val is None and api_val:
            continue  # Optional field present in API only
        if api_val is None and ext_val:
            if field == "incorporation_date":
                continue  # Optional
            flags.append({"field": field, "extracted": ext_val, "api": None})
            continue

        if field == "company_number":
            # Normalize: strip, uppercase, zero-pad to 8 digits
            a = str(ext_val).strip().upper().replace(" ", "")
            b = str(api_val).strip().upper().replace(" ", "")
            if len(a) < 8:
                a = a.zfill(8)
            if len(b) < 8:
                b = b.zfill(8)
            match = a == b
        elif field == "registered_office_address":
            match = _values_match(ext_val, api_val, _normalize_address)
        elif field == "incorporation_date":
            # Dates may differ in format (YYYY-MM-DD vs DD/MM/YYYY)
            a = re.sub(r"\D", "", str(ext_val))
            b = re.sub(r"\D", "", str(api_val))
            match = a == b
        else:
            match = _values_match(ext_val, api_val)

        if not match:
            flags.append({"field": field, "extracted": ext_val, "api": api_val})

    status = VERIFIED if not flags else DISCREPANCY_FLAG
    return status, flags, compared


def _verify_land_registry(
    extracted: dict[str, Any], api: dict[str, Any]
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """
    Verify Land Registry extraction against API response (free tier).

    Free tier only provides: property_address, tenure, transactions.
    title_number and proprietor_name are NOT verifiable (always None from API).
    """
    flags: list[dict[str, Any]] = []
    compared: list[str] = []

    # property_address: match by postcode (we search by postcode; API returns same-postcode data)
    ext_addr = extracted.get("property_address")
    api_addr = api.get("property_address")
    compared.append("property_address")
    if ext_addr and api_addr:
        ext_pc = _extract_postcode(ext_addr)
        api_pc = _extract_postcode(api_addr)
        if ext_pc and api_pc:
            if ext_pc != api_pc:
                flags.append({"field": "property_address", "extracted": ext_addr, "api": api_addr})
        elif not _values_match(ext_addr, api_addr, _normalize_address):
            flags.append({"field": "property_address", "extracted": ext_addr, "api": api_addr})
    elif ext_addr and not api_addr:
        flags.append({"field": "property_address", "extracted": ext_addr, "api": None})
    # If api has address but extracted doesn't - extraction may be incomplete

    # tenure: Freehold/Leasehold (case-insensitive)
    ext_tenure = extracted.get("tenure")
    api_tenure = api.get("tenure")
    compared.append("tenure")
    if ext_tenure and api_tenure:
        if not _values_match(ext_tenure, api_tenure):
            flags.append({"field": "tenure", "extracted": ext_tenure, "api": api_tenure})
    # If api has no tenure (None) we can't verify - don't flag
    # If extracted has tenure but api doesn't - free tier may not have it for all properties

    # title_number, proprietor_name: NOT verifiable in free tier - skip
    compared.append("title_number")
    compared.append("proprietor_name")

    status = VERIFIED if not flags else DISCREPANCY_FLAG
    return status, flags, compared


def _verify_epc(
    extracted: dict[str, Any], api: dict[str, Any]
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """
    Verify EPC extraction against API response.

    EPC API returns rows; we compare reference_number (lmk-key), address, rating.
    """
    fields = [
        "reference_number",
        "property_address",
        "current_energy_rating",
        "total_floor_area",
    ]
    flags: list[dict[str, Any]] = []
    compared: list[str] = []

    # EPC API may return a list of rows (search) or single cert
    api_row = api
    if isinstance(api, list) and api:
        api_row = api[0]
    elif not isinstance(api_row, dict):
        flags.append({"field": "api", "extracted": None, "api": "Invalid API response format"})
        return DISCREPANCY_FLAG, flags, []

    # Map EPC API field names (may differ from our schema)
    api_ref = api_row.get("lmk-key") or api_row.get("reference_number")
    api_addr = api_row.get("address") or api_row.get("property_address")
    api_rating = api_row.get("current-energy-rating") or api_row.get("current_energy_rating")
    api_floor = api_row.get("total-floor-area") or api_row.get("total_floor_area")

    for field in fields:
        compared.append(field)
        ext_val = extracted.get(field)
        if field == "reference_number":
            api_val = api_ref
        elif field == "property_address":
            api_val = api_addr
        elif field == "current_energy_rating":
            api_val = api_rating
        elif field == "total_floor_area":
            api_val = api_floor
        else:
            api_val = api_row.get(field)

        if ext_val is None and api_val is None:
            continue
        if api_val is None:
            flags.append({"field": field, "extracted": ext_val, "api": None})
            continue

        if field == "property_address":
            match = _values_match(ext_val, api_val, _normalize_address)
        else:
            match = _values_match(ext_val, api_val)

        if not match:
            flags.append({"field": field, "extracted": ext_val, "api": api_val})

    status = VERIFIED if not flags else DISCREPANCY_FLAG
    return status, flags, compared


def _normalize_numeric(val: Any) -> str:
    """Normalize numeric string for comparison (strip currency, commas, whitespace)."""
    if val is None:
        return ""
    s = str(val).strip()
    s = re.sub(r"[$€£¥,\s]", "", s)
    return s.lower()


def _verify_financial(
    extracted: dict[str, Any], api: dict[str, Any]
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """
    Verify financial extraction against API (e.g. SEC EDGAR when available).
    Used when external verification source exists (US SEC filings).
    """
    numeric_fields = {"revenue", "net_income", "total_assets", "eps_diluted"}
    flags: list[dict[str, Any]] = []
    compared: list[str] = []

    for field in ["company_name", "cik", "filing_type", "period_end_date", "revenue", "net_income", "total_assets", "eps_diluted"]:
        ext_val = extracted.get(field)
        api_val = api.get(field)
        compared.append(field)

        if ext_val is None and api_val is None:
            continue
        if ext_val is None and api_val:
            continue
        if api_val is None and ext_val:
            continue  # Optional field

        if field in numeric_fields:
            a = _normalize_numeric(ext_val)
            b = _normalize_numeric(api_val)
            match = a == b
        else:
            match = _values_match(ext_val, api_val)

        if not match:
            flags.append({"field": field, "extracted": ext_val, "api": api_val})

    status = VERIFIED if not flags else DISCREPANCY_FLAG
    return status, flags, compared


def verify_extraction(
    audit_target: str | AuditTarget,
    extracted_json: dict[str, Any],
    api_response_json: dict[str, Any] | None,
) -> VerificationResult:
    """
    Compare extracted document data against API response.

    Args:
        audit_target: companies_house, hm_land_registry, or epc
        extracted_json: Structured extraction from LLM (matches schema for target)
        api_response_json: Response from external API, or None if API failed/unavailable

    Returns:
        VerificationResult with status (VERIFIED or DISCREPANCY_FLAG),
        discrepancy_flags (list of {field, extracted, api}),
        fields_compared (list of field names)
    """
    if isinstance(audit_target, str):
        try:
            audit_target = AuditTarget(audit_target)
        except ValueError:
            logger.error("Unknown audit_target: %s", audit_target)
            return VerificationResult(
                status=DISCREPANCY_FLAG,
                discrepancy_flags=[{"field": "audit_target", "extracted": audit_target, "api": "Unknown target"}],
                fields_compared=[],
            )

    if api_response_json is None:
        # No external registry: financial docs, or multimodal vision_poc POC
        if audit_target in (AuditTarget.FINANCIAL, AuditTarget.VISION_POC):
            return VerificationResult(
                status=EXTRACTED,
                discrepancy_flags=[],
                fields_compared=[],
            )
        return VerificationResult(
            status=DISCREPANCY_FLAG,
            discrepancy_flags=[{"field": "api", "extracted": "available", "api": "API unavailable or failed"}],
            fields_compared=[],
        )

    if not isinstance(extracted_json, dict):
        return VerificationResult(
            status=DISCREPANCY_FLAG,
            discrepancy_flags=[{"field": "extraction", "extracted": type(extracted_json).__name__, "api": "Expected dict"}],
            fields_compared=[],
        )

    if audit_target == AuditTarget.COMPANIES_HOUSE:
        status, flags, compared = _verify_companies_house(extracted_json, api_response_json)
    elif audit_target == AuditTarget.HM_LAND_REGISTRY:
        status, flags, compared = _verify_land_registry(extracted_json, api_response_json)
    elif audit_target == AuditTarget.EPC:
        status, flags, compared = _verify_epc(extracted_json, api_response_json)
    elif audit_target == AuditTarget.FINANCIAL:
        status, flags, compared = _verify_financial(extracted_json, api_response_json)
    else:
        return VerificationResult(
            status=DISCREPANCY_FLAG,
            discrepancy_flags=[{"field": "audit_target", "extracted": audit_target.value, "api": "No verifier"}],
            fields_compared=[],
        )

    return VerificationResult(status=status, discrepancy_flags=flags, fields_compared=compared)
