"""
HM Land Registry API client for AVAE verification (free tier).

Uses the Price Paid Data SPARQL endpoint at landregistry.data.gov.uk.
No registration or API key required. Data under Open Government Licence.

Verifies: property address, sale history, tenure (estate type).
Does NOT provide: title number, registered proprietor (Business Gateway only).
"""
import json
import logging
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://landregistry.data.gov.uk/landregistry/sparql"

# UK postcode pattern (outcode + incode): e.g. EC1V 3AP, SW1A 1AA, M1 1AA
UK_POSTCODE_PATTERN = re.compile(
    r"\b([A-Z]{1,2}[0-9][0-9A-Z]?)\s*([0-9][A-Z]{2})\b",
    re.IGNORECASE,
)


def _extract_postcode(address: str) -> str | None:
    """Extract UK postcode from address string. Returns None if not found."""
    if not address or not isinstance(address, str):
        return None
    match = UK_POSTCODE_PATTERN.search(address.strip())
    if match:
        # Normalize: uppercase, space between outcode and incode
        return f"{match.group(1).upper()} {match.group(2).upper()}"
    return None


def _build_sparql_query(postcode: str, limit: int = 20) -> str:
    """Build SPARQL query for Price Paid Data by postcode."""
    return f"""
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>

SELECT ?paon ?saon ?street ?locality ?town ?district ?county ?postcode
       ?amount ?date ?propertyType ?estateType ?transactionCategory
WHERE {{
    ?transx lrppi:pricePaid ?amount ;
            lrppi:transactionDate ?date ;
            lrppi:propertyAddress ?addr ;
            lrppi:propertyType ?propertyType ;
            lrppi:estateType ?estateType ;
            lrppi:transactionCategory ?transactionCategory .
    ?addr lrcommon:postcode ?postcode .
    OPTIONAL {{ ?addr lrcommon:paon ?paon . }}
    OPTIONAL {{ ?addr lrcommon:saon ?saon . }}
    OPTIONAL {{ ?addr lrcommon:street ?street . }}
    OPTIONAL {{ ?addr lrcommon:locality ?locality . }}
    OPTIONAL {{ ?addr lrcommon:town ?town . }}
    OPTIONAL {{ ?addr lrcommon:district ?district . }}
    OPTIONAL {{ ?addr lrcommon:county ?county . }}
    FILTER(regex(?postcode, "{_sparql_escape(postcode)}", "i"))
}}
ORDER BY DESC(?date)
LIMIT {limit}
""".strip()


def _sparql_escape(s: str) -> str:
    """Escape string for safe use in SPARQL FILTER regex."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _format_address(row: dict[str, Any]) -> str:
    """Format address from parsed SPARQL row (plain key->value dict)."""
    parts = []
    for key in ["paon", "saon", "street", "locality", "town", "district", "county", "postcode"]:
        val = row.get(key)
        if val:
            parts.append(str(val))
    return ", ".join(parts) if parts else ""


def _parse_sparql_results(data: dict) -> list[dict[str, Any]]:
    """Parse SPARQL JSON results into list of transaction dicts."""
    results = []
    try:
        bindings_list = data.get("results", {}).get("bindings", [])
    except (AttributeError, TypeError):
        return results

    for b in bindings_list:
        row = {}
        for key, obj in b.items():
            if isinstance(obj, dict) and "value" in obj:
                row[key] = obj["value"]
        if row:
            results.append(row)
    return results


def _infer_tenure(transactions: list[dict[str, Any]]) -> str | None:
    """Infer tenure (freehold/leasehold) from estateType in transactions."""
    for t in transactions:
        et = t.get("estateType")
        if et:
            et_lower = str(et).lower()
            if "freehold" in et_lower:
                return "Freehold"
            if "leasehold" in et_lower:
                return "Leasehold"
    return None


def fetch_land_data(property_address: str, title_number: str | None = None) -> dict | None:
    """
    Fetch property data from HM Land Registry Price Paid Data (free tier).

    Searches by postcode extracted from property_address. Returns transaction
    history and inferred tenure. Title number and proprietor are not available
    in the free tier.

    Args:
        property_address: Full property address (postcode used for lookup).
        title_number: Ignored in free tier; reserved for future Business Gateway.

    Returns:
        Normalized dict with:
          - property_address: Formatted address from first match
          - tenure: Freehold/Leasehold if inferrable from transactions
          - transactions: List of {amount, date, propertyType, estateType, ...}
          - title_number: None (not available in free tier)
          - proprietor_name: None (not available in free tier)
        Or None on failure.
    """
    if not property_address or not str(property_address).strip():
        logger.warning("Land Registry fetch skipped: empty property_address")
        return None

    postcode = _extract_postcode(property_address)
    if not postcode:
        logger.warning(
            "Land Registry fetch skipped: no UK postcode found in '%s'",
            property_address[:80],
        )
        return None

    query = _build_sparql_query(postcode)
    params = urlencode({"query": query})
    url = f"{SPARQL_ENDPOINT}?{params}"

    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "AVAE-Document-Processor/1.0",
    }

    try:
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        logger.error("Land Registry HTTP error %s: %s", e.code, e.reason)
        return None
    except URLError as e:
        logger.error("Land Registry request failed: %s", e.reason)
        return None
    except (json.JSONDecodeError, TimeoutError) as e:
        logger.error("Land Registry parse/timeout error: %s", e)
        return None

    transactions = _parse_sparql_results(data)
    if not transactions:
        logger.info("Land Registry: no transactions found for postcode %s", postcode)
        return {
            "property_address": property_address,
            "tenure": None,
            "transactions": [],
            "title_number": None,
            "proprietor_name": None,
        }

    formatted_addr = _format_address(transactions[0]) or property_address
    tenure = _infer_tenure(transactions)

    return {
        "property_address": formatted_addr,
        "tenure": tenure,
        "transactions": transactions,
        "title_number": None,
        "proprietor_name": None,
    }
