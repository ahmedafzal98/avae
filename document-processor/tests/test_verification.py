"""
Test verification module (Task 2.3).

Run: cd document-processor && python -c "from tests.test_verification import *; test_all()"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.verification import verify_extraction, VERIFIED, DISCREPANCY_FLAG
from app.api_registry import AuditTarget


def test_companies_house_verified():
    """Companies House: all fields match -> VERIFIED."""
    extracted = {
        "company_number": "02578066",
        "company_name": "EXAMPLE LTD",
        "registered_office_address": "123 Example St, London SW1A 1AA",
        "company_status": "active",
        "company_type": "ltd",
        "incorporation_date": "1990-01-15",
    }
    api = {
        "company_number": "02578066",
        "company_name": "EXAMPLE LTD",
        "registered_office_address": "123 Example St, London SW1A 1AA",
        "company_status": "active",
        "company_type": "ltd",
        "incorporation_date": "1990-01-15",
    }
    r = verify_extraction(AuditTarget.COMPANIES_HOUSE, extracted, api)
    assert r.status == VERIFIED
    assert len(r.discrepancy_flags) == 0


def test_companies_house_discrepancy():
    """Companies House: company_name mismatch -> DISCREPANCY_FLAG."""
    extracted = {
        "company_number": "02578066",
        "company_name": "Acme Ltd",
        "registered_office_address": "123 Example St",
        "company_status": "active",
        "company_type": "ltd",
        "incorporation_date": None,
    }
    api = {
        "company_number": "02578066",
        "company_name": "Acme Limited",
        "registered_office_address": "123 Example St",
        "company_status": "active",
        "company_type": "ltd",
        "incorporation_date": None,
    }
    r = verify_extraction(AuditTarget.COMPANIES_HOUSE, extracted, api)
    assert r.status == DISCREPANCY_FLAG
    assert any(f["field"] == "company_name" for f in r.discrepancy_flags)


def test_land_registry_verified():
    """Land Registry: same postcode, same tenure -> VERIFIED."""
    extracted = {
        "title_number": "ABC123",
        "property_address": "25 Pear Tree Street, London EC1V 3AP",
        "tenure": "Leasehold",
        "proprietor_name": "John Doe",
    }
    api = {
        "property_address": "ORCHARD BUILDING, 25, PEAR TREE STREET, LONDON, EC1V 3AP",
        "tenure": "Leasehold",
        "transactions": [],
        "title_number": None,
        "proprietor_name": None,
    }
    r = verify_extraction(AuditTarget.HM_LAND_REGISTRY, extracted, api)
    assert r.status == VERIFIED


def test_land_registry_tenure_mismatch():
    """Land Registry: tenure mismatch -> DISCREPANCY_FLAG."""
    extracted = {
        "property_address": "25 Pear Tree Street, London EC1V 3AP",
        "tenure": "Freehold",
    }
    api = {
        "property_address": "25 PEAR TREE STREET, LONDON EC1V 3AP",
        "tenure": "Leasehold",
        "transactions": [],
    }
    r = verify_extraction(AuditTarget.HM_LAND_REGISTRY, extracted, api)
    assert r.status == DISCREPANCY_FLAG
    assert any(f["field"] == "tenure" for f in r.discrepancy_flags)


def test_api_unavailable():
    """API response None -> DISCREPANCY_FLAG."""
    extracted = {"company_number": "02578066", "company_name": "Test"}
    r = verify_extraction(AuditTarget.COMPANIES_HOUSE, extracted, None)
    assert r.status == DISCREPANCY_FLAG
    assert any("api" in str(f) for f in r.discrepancy_flags)


def test_all():
    test_companies_house_verified()
    test_companies_house_discrepancy()
    test_land_registry_verified()
    test_land_registry_tenure_mismatch()
    test_api_unavailable()
    print("All verification tests passed!")
