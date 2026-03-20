"""
Companies House API client for AVAE verification.

Fetches company data from the official Companies House API for comparison
against extracted document data.
"""
import base64
import json
import logging
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from app.config import settings
from app.api_registry import get_api_config, AuditTarget

logger = logging.getLogger(__name__)


def _format_address(addr: dict[str, Any] | None) -> str:
    """Format Companies House address object into single string."""
    if not addr or not isinstance(addr, dict):
        return ""
    parts = [
        addr.get("address_line_1"),
        addr.get("address_line_2"),
        addr.get("locality"),
        addr.get("postal_code"),
        addr.get("country"),
    ]
    return ", ".join(p for p in parts if p)


def fetch_company(company_number: str) -> dict | None:
    """
    Fetch company data from Companies House API.

    Args:
        company_number: 8-digit company number (e.g. "00000006", "02578066")

    Returns:
        Normalized dict with company_number, company_name, registered_office_address,
        company_status, company_type, incorporation_date; or None on failure
    """
    if not company_number or not str(company_number).strip():
        logger.warning("Companies House fetch skipped: empty company_number")
        return None

    api_key = settings.companies_house_api_key
    if not api_key:
        logger.warning("Companies House fetch skipped: COMPANIES_HOUSE_API_KEY not set")
        return None

    try:
        config = get_api_config(AuditTarget.COMPANIES_HOUSE)
    except ValueError as e:
        logger.error(f"Companies House config error: {e}")
        return None

    # Normalize company number (remove spaces, ensure 8 digits with leading zeros)
    cn = str(company_number).strip().upper().replace(" ", "")
    if len(cn) < 8:
        cn = cn.zfill(8)

    url = f"{config.base_url}{config.lookup_path}".replace("{id}", cn)

    # Basic auth: API key as username, empty password
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    headers = {
        "Accept": "application/json",
        "Authorization": f"Basic {credentials}",
    }

    try:
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 404:
            logger.info(f"Companies House: company {cn} not found")
        elif e.code == 401:
            logger.error("Companies House: invalid API key (401)")
        elif e.code == 429:
            logger.warning("Companies House: rate limit exceeded (429)")
        else:
            logger.error(f"Companies House HTTP error {e.code}: {e.reason}")
        return None
    except URLError as e:
        logger.error(f"Companies House request failed: {e.reason}")
        return None
    except (json.JSONDecodeError, TimeoutError) as e:
        logger.error(f"Companies House parse/timeout error: {e}")
        return None

    # Map API response to normalized structure (matches CorporateKYCExtraction)
    addr = data.get("registered_office_address")
    return {
        "company_number": data.get("company_number", cn),
        "company_name": data.get("company_name") or "",
        "registered_office_address": _format_address(addr),
        "company_status": data.get("company_status") or "",
        "company_type": data.get("type") or "",
        "incorporation_date": data.get("date_of_creation"),
    }
