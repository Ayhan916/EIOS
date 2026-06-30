"""CSV ERP Adapter — M6

Reads material and BOM data from CSV files/strings.
Most common format for initial ERP data exports (SAP SE16, Oracle BOM Export).

Column names are configurable via field_paths. Defaults assume a common
SAP material export header format.
"""

from __future__ import annotations

import csv
import io

import structlog

from .base import BaseERPAdapter, ERPBOMRecord, ERPDPPRecord, ERPMaterialRecord

logger = structlog.get_logger(__name__)

_DEFAULT_MATERIAL_COLS = {
    "external_ref": "MATNR",
    "name": "MAKTX",
    "material_type": "MTART",
    "unit_of_measure": "MEINS",
    "cas_number": "CAS_NUMBER",
    "description": "MAKTX",
    "country_of_origin": "HERKUNFTSLAND",
    "is_substance_of_concern": "SVHC_FLAG",
}

_DEFAULT_BOM_COLS = {
    "product_external_ref": "MATNR",
    "material_external_ref": "IDNRK",
    "quantity": "MENGE",
    "unit_of_measure": "MEINS",
    "weight_pct": "WEIGHT_PCT",
    "is_substance_of_concern": "SVHC_FLAG",
}


def _bool_val(v: str | None) -> bool:
    if v is None:
        return False
    return str(v).strip().upper() in ("1", "X", "TRUE", "YES", "J")


class CsvERPAdapter(BaseERPAdapter):
    """CSV-based ERP adapter — accepts raw CSV text or file path."""

    def __init__(
        self,
        materials_csv: str = "",
        bom_csv: str = "",
        field_paths: dict[str, dict[str, str]] | None = None,
        delimiter: str = ";",
    ) -> None:
        self._materials_csv = materials_csv
        self._bom_csv = bom_csv
        self._field_paths = field_paths or {}
        self._delimiter = delimiter

    async def test_connection(self) -> bool:
        return bool(self._materials_csv or self._bom_csv)

    async def fetch_materials(self) -> list[ERPMaterialRecord]:
        if not self._materials_csv:
            return []
        cols = {**_DEFAULT_MATERIAL_COLS, **self._field_paths.get("Material", {})}
        records: list[ERPMaterialRecord] = []
        reader = csv.DictReader(io.StringIO(self._materials_csv), delimiter=self._delimiter)
        for row in reader:
            ext_ref = row.get(cols["external_ref"], "").strip()
            if not ext_ref:
                continue
            records.append(ERPMaterialRecord(
                external_ref=ext_ref,
                name=row.get(cols["name"], ext_ref).strip(),
                material_type=row.get(cols["material_type"], "RAW_MATERIAL").strip() or "RAW_MATERIAL",
                cas_number=row.get(cols.get("cas_number", ""), "").strip() or None,
                unit_of_measure=row.get(cols.get("unit_of_measure", ""), "").strip() or None,
                description=row.get(cols.get("description", ""), "").strip() or None,
                country_of_origin=row.get(cols.get("country_of_origin", ""), "").strip() or None,
                is_substance_of_concern=_bool_val(row.get(cols.get("is_substance_of_concern", ""))),
                raw=dict(row),
            ))
        return records

    async def fetch_bom(self) -> list[ERPBOMRecord]:
        if not self._bom_csv:
            return []
        cols = {**_DEFAULT_BOM_COLS, **self._field_paths.get("BOM", {})}
        records: list[ERPBOMRecord] = []
        reader = csv.DictReader(io.StringIO(self._bom_csv), delimiter=self._delimiter)
        for row in reader:
            product_ref = row.get(cols["product_external_ref"], "").strip()
            material_ref = row.get(cols["material_external_ref"], "").strip()
            if not product_ref or not material_ref:
                continue
            try:
                qty = float(row.get(cols.get("quantity", ""), "1").strip() or 1.0)
            except ValueError:
                qty = 1.0
            try:
                weight_pct_raw = row.get(cols.get("weight_pct", ""), "").strip()
                weight_pct: float | None = float(weight_pct_raw) if weight_pct_raw else None
            except ValueError:
                weight_pct = None
            records.append(ERPBOMRecord(
                product_external_ref=product_ref,
                material_external_ref=material_ref,
                quantity=qty,
                unit_of_measure=row.get(cols.get("unit_of_measure", ""), "").strip() or None,
                weight_pct=weight_pct,
                is_substance_of_concern=_bool_val(row.get(cols.get("is_substance_of_concern", ""))),
                raw=dict(row),
            ))
        return records

    async def push_dpp(self, records: list[ERPDPPRecord]) -> dict:
        # CSV export — generate output CSV rows (caller decides what to do with it)
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self._delimiter)
        writer.writerow(["PassportUID", "ProductRef", "CarbonFootprint_kgCO2e",
                         "RecycledContent_pct", "SubstancesOfConcern", "NonCompliantRegs", "DisclosedAt"])
        for rec in records:
            writer.writerow([
                rec.passport_uid,
                rec.product_external_ref,
                rec.carbon_footprint_kg_co2e,
                rec.recycled_content_pct,
                rec.substances_of_concern_count,
                rec.non_compliant_regulations_count,
                rec.disclosed_at,
            ])
        return {"pushed": len(records), "failed": 0, "errors": [], "csv_output": output.getvalue()}
