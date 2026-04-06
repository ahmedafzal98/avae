"""
API Registry — Maps Audit Targets to external API configuration.

Used by the AVAE pipeline to dynamically select the correct API path,
auth, and ID field for ground-truth verification.

Add new audit targets by extending AUDIT_TARGET_CONFIG.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AuditTarget(str, Enum):
    """Supported audit targets for compliance verification."""
    COMPANIES_HOUSE = "companies_house"
    HM_LAND_REGISTRY = "hm_land_registry"
    EPC = "epc"
    FINANCIAL = "financial"
    # Multimodal POC: GPT-4o vision on PDF page images (no external verification API)
    VISION_POC = "vision_poc"


@dataclass(frozen=True)
class APIConfig:
    """
    Configuration for an external verification API.

    Attributes:
        base_url: API base URL (no trailing slash)
        id_field: Field name from extraction schema used as lookup key
        lookup_path: Path template for lookup; {id} is replaced with id_field value
        auth_type: "basic_api_key" | "basic_email_key" | "ssl_basic"
        auth_env_vars: Settings attribute names for auth (e.g. ["companies_house_api_key"])
        rate_limit_per_min: Max requests per minute (for throttling)
    """
    base_url: str
    id_field: str
    lookup_path: str
    auth_type: str
    auth_env_vars: tuple[str, ...]
    rate_limit_per_min: int = 60


# Registry: audit_target -> API config
AUDIT_TARGET_CONFIG: dict[AuditTarget, APIConfig] = {
    AuditTarget.EPC: APIConfig(
        base_url="https://epc.opendatacommunities.org/api/v1",
        id_field="reference_number",
        lookup_path="/domestic/search",
        auth_type="basic_email_key",
        auth_env_vars=("epc_api_email", "epc_api_key"),
        rate_limit_per_min=60,
    ),
    AuditTarget.COMPANIES_HOUSE: APIConfig(
        base_url="https://api.company-information.service.gov.uk",
        id_field="company_number",
        lookup_path="/company/{id}",
        auth_type="basic_api_key",
        auth_env_vars=("companies_house_api_key",),
        rate_limit_per_min=600,  # 10/sec typical limit
    ),
    AuditTarget.HM_LAND_REGISTRY: APIConfig(
        base_url="https://landregistry.data.gov.uk",
        id_field="property_address",
        lookup_path="/landregistry/sparql",
        auth_type="none",
        auth_env_vars=(),
        rate_limit_per_min=60,
    ),
    AuditTarget.FINANCIAL: APIConfig(
        base_url="https://data.sec.gov",
        id_field="cik",
        lookup_path="/api/xbrl/companyfacts/CIK{id}.json",
        auth_type="none",
        auth_env_vars=(),
        rate_limit_per_min=600,
    ),
}


def get_api_config(audit_target: AuditTarget | str) -> APIConfig:
    """
    Return API config for the given audit target.

    Args:
        audit_target: AuditTarget enum or string (e.g. "epc", "companies_house")

    Returns:
        APIConfig for the target

    Raises:
        ValueError: If audit target has no API config
    """
    if isinstance(audit_target, str):
        try:
            audit_target = AuditTarget(audit_target)
        except ValueError:
            raise ValueError(f"Unknown audit target: {audit_target}")
    config = AUDIT_TARGET_CONFIG.get(audit_target)
    if not config:
        raise ValueError(f"No API config for audit target: {audit_target}")
    return config


def get_valid_audit_targets() -> list[str]:
    """Return list of valid audit_target string values for validation and error messages."""
    return [t.value for t in AuditTarget]


def validate_audit_target(value: Optional[str]) -> str:
    """
    Validate audit_target and return normalized value.
    Returns default 'epc' if None or empty.
    Raises ValueError if invalid.
    """
    if not value or not str(value).strip():
        return AuditTarget.EPC.value
    normalized = str(value).strip().lower()
    valid = get_valid_audit_targets()
    if normalized not in valid:
        raise ValueError(f"Invalid audit_target. Allowed: {', '.join(valid)}")
    return normalized
