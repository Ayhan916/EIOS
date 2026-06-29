"""M48.1 G-042 — OFAC SDN Connector.

Downloads the OFAC Specially Designated Nationals (SDN) list in XML format,
parses it, and upserts ExternalRiskSignals for matched supplier names.

Source: https://ofac.treasury.gov/downloads/sdn.xml
Schedule: daily at 04:00 UTC (configured in Celery beat schedule).

SDN XML schema: https://ofac.treasury.gov/media/4076/download?inline
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx
from lxml import etree

logger = logging.getLogger(__name__)

OFAC_SDN_URL = "https://ofac.treasury.gov/downloads/sdn.xml"
_TIMEOUT = 60.0
_SDN_NS = "http://tempuri.org/sdnList.xsd"


def _ns(tag: str) -> str:
    return f"{{{_SDN_NS}}}{tag}"


async def fetch_sdn_xml() -> bytes:
    """Download the OFAC SDN list XML. Returns raw bytes."""
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(OFAC_SDN_URL)
        response.raise_for_status()
        return response.content


def parse_sdn_entries(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse SDN XML into a list of entity dicts.

    Each dict has:
        uid, type, name, programs (list[str]), addresses (list[str])
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        logger.error("ofac_xml_parse_error: %s", exc)
        return []

    entries: list[dict[str, Any]] = []

    for sdn_entry in root.findall(_ns("sdnEntry")):
        uid_el = sdn_entry.find(_ns("uid"))
        type_el = sdn_entry.find(_ns("sdnType"))
        lastname_el = sdn_entry.find(_ns("lastName"))
        firstname_el = sdn_entry.find(_ns("firstName"))

        if uid_el is None or lastname_el is None:
            continue

        uid = uid_el.text or ""
        sdn_type = type_el.text if type_el is not None else "Unknown"
        last = lastname_el.text or ""
        first = (firstname_el.text or "") if firstname_el is not None else ""
        full_name = f"{first} {last}".strip() if first else last

        programs = [
            p.text or ""
            for p in sdn_entry.findall(f".//{_ns('program')}")
        ]

        addresses = []
        for addr in sdn_entry.findall(f".//{_ns('address')}"):
            parts = []
            for field in ("city", "country"):
                el = addr.find(_ns(field))
                if el is not None and el.text:
                    parts.append(el.text)
            if parts:
                addresses.append(", ".join(parts))

        entries.append({
            "uid": uid,
            "type": sdn_type,
            "name": full_name,
            "programs": programs,
            "addresses": addresses,
        })

    logger.info("ofac_sdn_parsed: %d entries", len(entries))
    return entries


def match_supplier_against_sdn(
    supplier_name: str,
    sdn_entries: list[dict[str, Any]],
    *,
    fuzzy: bool = False,
) -> list[dict[str, Any]]:
    """Return SDN entries whose name matches the supplier name.

    Exact case-insensitive match only (fuzzy=False, default).
    fuzzy=True does a simple contains check — higher recall, lower precision.
    """
    needle = supplier_name.strip().lower()
    matches = []
    for entry in sdn_entries:
        haystack = entry["name"].lower()
        if fuzzy:
            hit = needle in haystack or haystack in needle
        else:
            hit = needle == haystack
        if hit:
            matches.append(entry)
    return matches


def sdn_entry_to_signal(
    entry: dict[str, Any],
    *,
    supplier_id: str,
    organization_id: str,
) -> dict[str, Any]:
    """Convert a matched SDN entry into an ExternalRiskSignal dict for upsert."""
    detail = {
        "ofac_uid": entry["uid"],
        "sdn_type": entry["type"],
        "programs": entry["programs"],
        "addresses": entry["addresses"],
    }
    signal_hash = hashlib.sha256(
        f"ofac:{entry['uid']}:{supplier_id}".encode()
    ).hexdigest()[:16]

    return {
        "signal_type": "SANCTIONS_MATCH",
        "source": "OFAC_SDN",
        "title": f"OFAC SDN match: {entry['name']}",
        "description": (
            f"Supplier name matched OFAC SDN list entry {entry['uid']} "
            f"({entry['type']}). Programs: {', '.join(entry['programs'][:3])}."
        ),
        "severity": "CRITICAL",
        "supplier_id": supplier_id,
        "organization_id": organization_id,
        "external_id": f"ofac_{entry['uid']}",
        "dedup_key": signal_hash,
        "raw_data": detail,
    }
