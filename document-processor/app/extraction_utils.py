"""Helpers for cleaning structured extraction output before persist and API responses."""
from typing import Any


def field_has_value(v: Any) -> bool:
    """True if v is a non-empty string, non-empty collection, or other truthy scalar."""
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict, set)):
        return len(v) > 0
    return True


def strip_empty_extraction_fields(data: dict[str, Any] | None) -> dict[str, Any]:
    """
    Remove keys whose values are None, blank strings, or empty collections.
    Used for vision_poc so UI and APIs only show fields present in the document.
    """
    if not data:
        return {}
    out: dict[str, Any] = {}
    for k, v in data.items():
        if not field_has_value(v):
            continue
        if isinstance(v, str):
            out[k] = v.strip()
        else:
            out[k] = v
    return out
