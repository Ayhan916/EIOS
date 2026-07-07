"""REST ERP Adapter — M6

Generic HTTP adapter for SAP OData v4 / Oracle REST / any REST ERP.
Handles pagination, auth headers, and JSON-path extraction.

In production: base_url + auth headers are resolved from the SecretReference
at runtime via the SecretProvider service. Tests inject a mock httpx client.
"""

from __future__ import annotations

import httpx
import structlog

from .base import BaseERPAdapter, ERPBOMRecord, ERPDPPRecord, ERPMaterialRecord

logger = structlog.get_logger(__name__)

# Default JSON paths for SAP S/4HANA OData v4 material API
_SAP_MATERIAL_PATHS = {
    "external_ref": "Material",
    "name": "MaterialName",
    "material_type": "MaterialType",
    "unit_of_measure": "BaseUnit",
    "description": "MaterialDescription",
}

_SAP_BOM_PATHS = {
    "product_external_ref": "Material",
    "material_external_ref": "BOMComponent",
    "quantity": "ComponentQuantity",
    "unit_of_measure": "ComponentUnit",
}


def _extract(record: dict, paths: dict[str, str]) -> dict:
    return {key: record.get(path) for key, path in paths.items()}


class RestERPAdapter(BaseERPAdapter):
    """Generic REST adapter — supports SAP OData, Oracle Fusion REST, and any JSON API."""

    def __init__(
        self,
        base_url: str,
        auth_headers: dict[str, str] | None = None,
        timeout_seconds: int = 30,
        field_paths: dict[str, dict[str, str]] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth_headers = auth_headers or {}
        self._timeout = timeout_seconds
        self._field_paths = field_paths or {}
        self._client = http_client  # injected in tests; created lazily in production

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._auth_headers,
            timeout=self._timeout,
        )

    async def test_connection(self) -> bool:
        try:
            async with self._get_client() as c:
                resp = await c.get("/")
                return resp.status_code < 500
        except Exception as exc:
            logger.warning("erp_rest_connection_failed", error=str(exc))
            return False

    async def fetch_materials(self) -> list[ERPMaterialRecord]:
        paths = self._field_paths.get("Material", _SAP_MATERIAL_PATHS)
        records: list[ERPMaterialRecord] = []
        try:
            async with self._get_client() as c:
                resp = await c.get("/API_MATERIAL_DOCUMENT_SRV/A_MaterialDocHeader")
                resp.raise_for_status()
                items = resp.json().get(
                    "value", resp.json() if isinstance(resp.json(), list) else []
                )
        except Exception as exc:
            logger.error("erp_rest_fetch_materials_failed", error=str(exc))
            return []

        for raw in items:
            extracted = _extract(raw, paths)
            if not extracted.get("external_ref"):
                continue
            records.append(
                ERPMaterialRecord(
                    external_ref=str(extracted["external_ref"]),
                    name=str(extracted.get("name") or extracted["external_ref"]),
                    material_type=str(extracted.get("material_type") or "RAW_MATERIAL"),
                    unit_of_measure=extracted.get("unit_of_measure"),
                    description=extracted.get("description"),
                    raw=raw,
                )
            )
        return records

    async def fetch_bom(self) -> list[ERPBOMRecord]:
        paths = self._field_paths.get("BOM", _SAP_BOM_PATHS)
        records: list[ERPBOMRecord] = []
        try:
            async with self._get_client() as c:
                resp = await c.get("/API_BILL_OF_MATERIAL_SRV/A_BillOfMaterialItem")
                resp.raise_for_status()
                items = resp.json().get(
                    "value", resp.json() if isinstance(resp.json(), list) else []
                )
        except Exception as exc:
            logger.error("erp_rest_fetch_bom_failed", error=str(exc))
            return []

        for raw in items:
            extracted = _extract(raw, paths)
            if not extracted.get("product_external_ref") or not extracted.get(
                "material_external_ref"
            ):
                continue
            try:
                qty = float(extracted.get("quantity") or 1.0)
            except (TypeError, ValueError):
                qty = 1.0
            records.append(
                ERPBOMRecord(
                    product_external_ref=str(extracted["product_external_ref"]),
                    material_external_ref=str(extracted["material_external_ref"]),
                    quantity=qty,
                    unit_of_measure=extracted.get("unit_of_measure"),
                    raw=raw,
                )
            )
        return records

    async def push_dpp(self, records: list[ERPDPPRecord]) -> dict:
        pushed = 0
        failed = 0
        errors: list[str] = []
        endpoint = "/API_DPP_SRV/A_DigitalProductPassport"

        try:
            async with self._get_client() as c:
                for rec in records:
                    try:
                        payload = {
                            "PassportUID": rec.passport_uid,
                            "Product": rec.product_external_ref,
                            "CarbonFootprint": rec.carbon_footprint_kg_co2e,
                            "RecycledContent": rec.recycled_content_pct,
                            "SubstancesOfConcern": rec.substances_of_concern_count,
                            "DisclosedAt": rec.disclosed_at,
                        }
                        resp = await c.post(endpoint, json=payload)
                        resp.raise_for_status()
                        pushed += 1
                    except Exception as exc:
                        failed += 1
                        errors.append(f"{rec.passport_uid}: {exc}")
        except Exception as exc:
            logger.error("erp_rest_push_dpp_failed", error=str(exc))
            failed += len(records)
            errors.append(str(exc))

        return {"pushed": pushed, "failed": failed, "errors": errors[:10]}
