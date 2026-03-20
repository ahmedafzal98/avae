"""
AVAE external API clients for ground-truth verification.

Each client fetches data from official sources (Companies House, Land Registry, EPC)
for comparison against extracted document data.
"""
from app.clients.companies_house import fetch_company
from app.clients.land_registry import fetch_land_data

__all__ = ["fetch_company", "fetch_land_data"]
