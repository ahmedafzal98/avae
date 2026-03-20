"""
Structured extraction schemas for AVAE compliance verification.

Each schema corresponds to an Audit Target and defines the compliance
entities extracted from documents for verification against external APIs.

Used by the Structured LLM Node (Phase 1.4) and Verification module (Phase 2).
"""
from pydantic import BaseModel, Field
from typing import Optional

from app.api_registry import AuditTarget


# ---------------------------------------------------------------------------
# EPC (Energy Performance Certificate) — UK
# ---------------------------------------------------------------------------

class EPCExtraction(BaseModel):
    """Structured extraction for UK EPC documents."""
    reference_number: str = Field(description="The 20-digit RRN (Reference Number) formatted with dashes.")
    property_address: str = Field(description="The full address of the property being assessed.")
    current_energy_rating: str = Field(description="The current energy efficiency rating number (e.g., 49, 76).")
    assessor_name: str = Field(description="The full name of the energy assessor.")
    assessor_accreditation_number: str = Field(description="The accreditation number of the assessor.")
    total_floor_area: str = Field(description="The total floor area including unit (e.g., m2).")


# ---------------------------------------------------------------------------
# Corporate KYC — Companies House
# ---------------------------------------------------------------------------

class CorporateKYCExtraction(BaseModel):
    """Structured extraction for company documents (Companies House verification)."""
    company_number: str = Field(description="The 8-digit Companies House registration number.")
    company_name: str = Field(description="The registered company name.")
    registered_office_address: str = Field(description="The registered office address.")
    company_status: str = Field(description="Active, Dissolved, etc.")
    company_type: str = Field(description="ltd, plc, etc.")
    incorporation_date: Optional[str] = Field(default=None, description="Date of incorporation.")


# ---------------------------------------------------------------------------
# Land Registry — HM Land Registry
# ---------------------------------------------------------------------------

class LandRegistryExtraction(BaseModel):
    """Structured extraction for land/title documents."""
    title_number: str = Field(description="The title number from HM Land Registry.")
    property_address: str = Field(description="The property address.")
    tenure: str = Field(description="Freehold or Leasehold.")
    proprietor_name: Optional[str] = Field(default=None, description="Name of registered proprietor.")


# ---------------------------------------------------------------------------
# Financial — Any financial statement (US SEC, UK, Pakistan PSX, etc.)
# ---------------------------------------------------------------------------

class FinancialExtraction(BaseModel):
    """Structured extraction for any financial document (annual reports, quarterly statements, etc.)."""
    company_name: str = Field(description="The company or issuer name.")
    exchange_or_jurisdiction: Optional[str] = Field(
        default=None,
        description="Stock exchange or jurisdiction (e.g. SEC, PSX, LSE, FCA, NSE).",
    )
    cik: Optional[str] = Field(
        default=None,
        description="US SEC 10-digit Central Index Key (CIK), if applicable.",
    )
    filing_type: Optional[str] = Field(
        default=None,
        description="Report type (10-K, 10-Q, annual report, quarterly report, etc.).",
    )
    period_end_date: Optional[str] = Field(
        default=None,
        description="Fiscal period end date (YYYY-MM-DD or similar).",
    )
    revenue: Optional[str] = Field(default=None, description="Total revenue for the period.")
    net_income: Optional[str] = Field(default=None, description="Net income (loss) for the period.")
    total_assets: Optional[str] = Field(default=None, description="Total assets.")
    eps_diluted: Optional[str] = Field(default=None, description="Diluted earnings per share.")


# ---------------------------------------------------------------------------
# Schema Registry — Maps Audit Target to Pydantic model
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMA_BY_TARGET = {
    AuditTarget.EPC: EPCExtraction,
    AuditTarget.COMPANIES_HOUSE: CorporateKYCExtraction,
    AuditTarget.HM_LAND_REGISTRY: LandRegistryExtraction,
    AuditTarget.FINANCIAL: FinancialExtraction,
}


def get_extraction_schema(audit_target: AuditTarget | str) -> type[BaseModel]:
    """
    Return the Pydantic extraction schema for the given audit target.

    Args:
        audit_target: AuditTarget enum or string (e.g., "epc", "companies_house")

    Returns:
        The Pydantic model class (e.g., EPCExtraction)

    Raises:
        ValueError: If audit target has no extraction schema
    """
    if isinstance(audit_target, str):
        try:
            audit_target = AuditTarget(audit_target)
        except ValueError:
            raise ValueError(f"Unknown audit target: {audit_target}")
    schema = EXTRACTION_SCHEMA_BY_TARGET.get(audit_target)
    if not schema:
        raise ValueError(f"No extraction schema for audit target: {audit_target}")
    return schema
