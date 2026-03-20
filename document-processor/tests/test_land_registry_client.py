"""
Test HM Land Registry client (free tier - Price Paid Data SPARQL).

Run: python -m pytest tests/test_land_registry_client.py -v
Or:  cd document-processor && python -c "from tests.test_land_registry_client import *; test_fetch_land_data()"
"""
import sys
from pathlib import Path

# Ensure app is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.land_registry import (
    fetch_land_data,
    _extract_postcode,
    _infer_tenure,
)


def test_extract_postcode():
    """Test UK postcode extraction from address strings."""
    assert _extract_postcode("10 Downing Street, London SW1A 2AA") == "SW1A 2AA"
    assert _extract_postcode("Flat 22, 25 Pear Tree Street, EC1V 3AP") == "EC1V 3AP"
    assert _extract_postcode("M1 1AA") == "M1 1AA"
    assert _extract_postcode("no postcode here") is None
    assert _extract_postcode("") is None


def test_infer_tenure():
    """Test tenure inference from estateType in transactions."""
    assert _infer_tenure([{"estateType": "http://landregistry.data.gov.uk/def/common/leasehold"}]) == "Leasehold"
    assert _infer_tenure([{"estateType": "http://landregistry.data.gov.uk/def/common/freehold"}]) == "Freehold"
    assert _infer_tenure([]) is None
    assert _infer_tenure([{"estateType": "other"}]) is None


def test_fetch_land_data():
    """Test fetch_land_data against live HM Land Registry SPARQL endpoint."""
    # Use a postcode known to have Price Paid data (Islington, London)
    result = fetch_land_data("25 Pear Tree Street, London EC1V 3AP")
    assert result is not None
    assert "property_address" in result
    assert "tenure" in result
    assert "transactions" in result
    assert result["title_number"] is None
    assert result["proprietor_name"] is None

    if result["transactions"]:
        tx = result["transactions"][0]
        assert "amount" in tx or "pricePaid" in tx or "date" in tx
        assert result["tenure"] in ("Freehold", "Leasehold", None)


def test_fetch_land_data_empty_address():
    """Empty address should return None."""
    assert fetch_land_data("") is None
    assert fetch_land_data("   ") is None


def test_fetch_land_data_no_postcode():
    """Address without UK postcode should return None."""
    assert fetch_land_data("123 Main Street, New York") is None
