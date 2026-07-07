"""ERP Sync Service — M6

Orchestrates inbound and outbound syncs between an ERP connector and the
Material/Product Twin + DPP layers.

run_inbound_sync()  — ERP → EIOS: materialize ERPMaterialRecords as MaterialModel rows
                      and ERPBOMRecords as ProductBOMItemModel rows.
run_outbound_sync() — EIOS → ERP: collect all active DPPs for the org, push to ERP.

Session ownership: sync_service commits after each batch.
organization_id is enforced on every DB query.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.erp.adapters.base import BaseERPAdapter, ERPDPPRecord
from infrastructure.persistence.models.dpp import DigitalProductPassportModel
from infrastructure.persistence.models.erp import ERPSyncJobModel
from infrastructure.persistence.models.material import MaterialModel
from infrastructure.persistence.models.product import ProductBOMItemModel, ProductModel

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _uid() -> str:
    return str(uuid4())


class ERPSyncService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Job lifecycle ──────────────────────────────────────────────────────────

    async def _create_job(
        self,
        organization_id: str,
        connector_id: str,
        direction: str,
        entity_type: str,
        actor_id: str | None = None,
    ) -> ERPSyncJobModel:
        now = _now()
        job = ERPSyncJobModel(
            id=_uid(),
            organization_id=organization_id,
            connector_id=connector_id,
            direction=direction,
            entity_type=entity_type,
            job_status="RUNNING",
            trigger_source="manual",
            initiated_by=actor_id,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def _finish_job(
        self,
        job: ERPSyncJobModel,
        *,
        fetched: int = 0,
        created: int = 0,
        updated: int = 0,
        failed: int = 0,
        error_message: str | None = None,
        error_details: list | None = None,
    ) -> None:
        end = _now()
        duration = (end - job.started_at).total_seconds() if job.started_at else 0.0
        job.records_fetched = fetched
        job.records_created = created
        job.records_updated = updated
        job.records_failed = failed
        job.job_status = "FAILED" if error_message else "SUCCESS"
        job.error_message = error_message
        job.error_details_json = json.dumps((error_details or [])[:100])
        job.completed_at = end
        job.runtime_seconds = f"{duration:.2f}"
        job.updated_at = end
        await self._session.commit()

    # ── Inbound sync: ERP → EIOS ───────────────────────────────────────────────

    async def run_inbound_sync(
        self,
        organization_id: str,
        connector_id: str,
        adapter: BaseERPAdapter,
        entity_type: str = "Material",
        actor_id: str | None = None,
    ) -> ERPSyncJobModel:
        """Pull data from ERP and upsert into EIOS Material + BOM tables."""
        job = await self._create_job(
            organization_id, connector_id, "INBOUND", entity_type, actor_id
        )
        errors: list[str] = []
        created = updated = failed = fetched = 0

        try:
            if entity_type == "Material":
                records = await adapter.fetch_materials()
                fetched = len(records)
                for rec in records:
                    try:
                        stmt = select(MaterialModel).where(
                            MaterialModel.organization_id == organization_id,
                            MaterialModel.external_ref == rec.external_ref,
                        )
                        result = await self._session.execute(stmt)
                        existing = result.scalar_one_or_none()

                        if existing:
                            existing.name = rec.name
                            existing.unit_of_measure = rec.unit_of_measure
                            existing.description = rec.description
                            existing.updated_at = _now()
                            updated += 1
                        else:
                            now = _now()
                            material = MaterialModel(
                                id=_uid(),
                                organization_id=organization_id,
                                external_ref=rec.external_ref,
                                name=rec.name,
                                material_type=rec.material_type,
                                cas_number=rec.cas_number,
                                unit_of_measure=rec.unit_of_measure,
                                description=rec.description,
                                country_of_origin=rec.country_of_origin,
                                status="Draft",
                                version=1,
                                created_at=now,
                                updated_at=now,
                                created_by=actor_id,
                            )
                            self._session.add(material)
                            created += 1
                    except Exception as exc:
                        failed += 1
                        errors.append(f"{rec.external_ref}: {exc}")

                await self._session.flush()

            elif entity_type == "BOM":
                records = await adapter.fetch_bom()
                fetched = len(records)
                for rec in records:
                    try:
                        # Resolve product and material by external_ref
                        prod_stmt = select(ProductModel.id).where(
                            ProductModel.organization_id == organization_id,
                            ProductModel.external_ref == rec.product_external_ref,
                        )
                        mat_stmt = select(MaterialModel.id).where(
                            MaterialModel.organization_id == organization_id,
                            MaterialModel.external_ref == rec.material_external_ref,
                        )
                        prod_result = await self._session.execute(prod_stmt)
                        mat_result = await self._session.execute(mat_stmt)
                        product_id = prod_result.scalar_one_or_none()
                        material_id = mat_result.scalar_one_or_none()

                        if not product_id or not material_id:
                            errors.append(
                                f"BOM {rec.product_external_ref}/{rec.material_external_ref}: "
                                "product or material not found in EIOS"
                            )
                            failed += 1
                            continue

                        existing_stmt = select(ProductBOMItemModel).where(
                            ProductBOMItemModel.organization_id == organization_id,
                            ProductBOMItemModel.product_id == product_id,
                            ProductBOMItemModel.material_id == material_id,
                        )
                        existing_result = await self._session.execute(existing_stmt)
                        existing_bom = existing_result.scalar_one_or_none()

                        if existing_bom:
                            existing_bom.quantity = rec.quantity
                            existing_bom.unit_of_measure = rec.unit_of_measure
                            existing_bom.weight_pct = rec.weight_pct
                            existing_bom.is_substance_of_concern = rec.is_substance_of_concern
                            existing_bom.updated_at = _now()
                            updated += 1
                        else:
                            now = _now()
                            bom_item = ProductBOMItemModel(
                                id=_uid(),
                                organization_id=organization_id,
                                product_id=product_id,
                                material_id=material_id,
                                quantity=rec.quantity,
                                unit_of_measure=rec.unit_of_measure,
                                weight_pct=rec.weight_pct,
                                is_substance_of_concern=rec.is_substance_of_concern,
                                created_at=now,
                                updated_at=now,
                            )
                            self._session.add(bom_item)
                            created += 1
                    except Exception as exc:
                        failed += 1
                        errors.append(f"BOM {rec.product_external_ref}: {exc}")

                await self._session.flush()

        except Exception as exc:
            await self._finish_job(
                job,
                fetched=fetched,
                created=created,
                updated=updated,
                failed=failed,
                error_message=str(exc),
                error_details=errors,
            )
            return job

        await self._finish_job(
            job,
            fetched=fetched,
            created=created,
            updated=updated,
            failed=failed,
            error_details=errors,
        )
        return job

    # ── Outbound sync: EIOS → ERP ──────────────────────────────────────────────

    async def run_outbound_sync(
        self,
        organization_id: str,
        connector_id: str,
        adapter: BaseERPAdapter,
        actor_id: str | None = None,
    ) -> ERPSyncJobModel:
        """Collect all active DPPs and push them to the ERP system."""
        job = await self._create_job(organization_id, connector_id, "OUTBOUND", "DPP", actor_id)

        try:
            stmt = select(DigitalProductPassportModel).where(
                DigitalProductPassportModel.organization_id == organization_id,
                DigitalProductPassportModel.dpp_status == "ACTIVE",
                DigitalProductPassportModel.disclosed_at.isnot(None),
            )
            result = await self._session.execute(stmt)
            dpps = list(result.scalars().all())

            records = [
                ERPDPPRecord(
                    passport_uid=dpp.passport_uid,
                    product_external_ref=dpp.product_id,
                    carbon_footprint_kg_co2e=dpp.carbon_footprint_kg_co2e,
                    recycled_content_pct=dpp.recycled_content_pct,
                    substances_of_concern_count=dpp.substances_of_concern_count,
                    non_compliant_regulations_count=dpp.non_compliant_regulations_count,
                    disclosed_at=dpp.disclosed_at.isoformat() if dpp.disclosed_at else None,
                )
                for dpp in dpps
            ]

            push_result = await adapter.push_dpp(records)
            pushed = push_result.get("pushed", 0)
            failed = push_result.get("failed", 0)
            errors = push_result.get("errors", [])

        except Exception as exc:
            await self._finish_job(job, error_message=str(exc))
            return job

        await self._finish_job(
            job,
            fetched=len(dpps),
            created=pushed,
            failed=failed,
            error_details=errors,
        )
        return job

    # ── Sync Job queries ───────────────────────────────────────────────────────

    async def list_jobs(
        self,
        organization_id: str,
        connector_id: str | None = None,
        job_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ERPSyncJobModel], int]:
        from sqlalchemy import func

        stmt = select(ERPSyncJobModel).where(
            ERPSyncJobModel.organization_id == organization_id,
        )
        if connector_id:
            stmt = stmt.where(ERPSyncJobModel.connector_id == connector_id)
        if job_status:
            stmt = stmt.where(ERPSyncJobModel.job_status == job_status)

        count_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()
        stmt = stmt.order_by(ERPSyncJobModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_job(self, organization_id: str, job_id: str) -> ERPSyncJobModel | None:
        model = await self._session.get(ERPSyncJobModel, job_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model
