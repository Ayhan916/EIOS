"""Retroaktive Entity-Verknüpfung: company_signals + company_metrics → supplier_id.

ADR-013: Deterministisches 3-Tier-Matching (exact=1.0, alias=0.9, fuzzy≥0.7).
         Kein LLM — reine String-Normalisierung + rapidfuzz.

Verwendung:
    cd backend
    python run_link_signals.py              # Standard (min_confidence=0.7)
    python run_link_signals.py --min 0.9   # Nur Exact + Alias-Matches
    python run_link_signals.py --dry-run   # Zeigt was verknüpft würde, ohne Commit
"""
import asyncio
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select, func

from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.models.organization import OrganizationModel
from infrastructure.persistence.models.company_intelligence import (
    CompanySignalModel,
    CompanyMetricModel,
)
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.models.entity_alias import EntityAliasModel
from application.intelligence.entity_linker_service import (
    load_candidates,
    link_signals,
    link_metrics,
)

TARGET_ORG_NAME = "EIOS"


async def _count_unlinked(org_id: str) -> tuple[int, int, int, int]:
    """Returns (signals_unlinked, signals_total, metrics_unlinked, metrics_total)."""
    async with AsyncSessionFactory() as db:
        s_unlinked = (await db.execute(
            select(func.count()).select_from(CompanySignalModel).where(
                CompanySignalModel.organization_id == org_id,
                CompanySignalModel.supplier_id.is_(None),
            )
        )).scalar_one()
        s_total = (await db.execute(
            select(func.count()).select_from(CompanySignalModel).where(
                CompanySignalModel.organization_id == org_id
            )
        )).scalar_one()
        m_unlinked = (await db.execute(
            select(func.count()).select_from(CompanyMetricModel).where(
                CompanyMetricModel.organization_id == org_id,
                CompanyMetricModel.supplier_id.is_(None),
            )
        )).scalar_one()
        m_total = (await db.execute(
            select(func.count()).select_from(CompanyMetricModel).where(
                CompanyMetricModel.organization_id == org_id
            )
        )).scalar_one()
    return s_unlinked, s_total, m_unlinked, m_total


async def _show_suppliers(org_id: str) -> None:
    async with AsyncSessionFactory() as db:
        suppliers = (await db.execute(
            select(SupplierModel.name, SupplierModel.legal_name, SupplierModel.id).where(
                SupplierModel.organization_id == org_id
            ).order_by(SupplierModel.name)
        )).all()
        alias_count = (await db.execute(
            select(func.count()).select_from(EntityAliasModel).where(
                EntityAliasModel.supplier_id.in_([s.id for s in suppliers])
            )
        )).scalar_one()

    print(f"   {len(suppliers)} Lieferanten ({alias_count} Aliases registriert):")
    for s in suppliers[:10]:
        legal = f" / {s.legal_name}" if s.legal_name else ""
        print(f"   • {s.name}{legal}")
    if len(suppliers) > 10:
        print(f"   … +{len(suppliers) - 10} weitere")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Link signals/metrics to suppliers.")
    parser.add_argument("--min", type=float, default=0.7, dest="min_confidence",
                        help="Minimum confidence threshold (default: 0.7)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only — no DB write")
    args = parser.parse_args()

    print("=" * 60)
    print("EIOS — Entity Linker: Signals + Metrics → Supplier")
    print(f"ADR-013 | min_confidence={args.min_confidence}"
          + (" | DRY-RUN" if args.dry_run else ""))
    print("=" * 60)

    # Organisation
    async with AsyncSessionFactory() as db:
        org = (await db.execute(
            select(OrganizationModel).where(OrganizationModel.name == TARGET_ORG_NAME).limit(1)
        )).scalar_one_or_none()
        if not org:
            org = (await db.execute(select(OrganizationModel).limit(1))).scalar_one_or_none()
        if not org:
            print("❌  Keine Organisation gefunden.")
            return
        org_id = str(org.id)

    print(f"\n✅  Organisation: {org.name} ({org_id[:8]}…)")
    await _show_suppliers(org_id)

    # Vorher-Zustand
    s_unlinked, s_total, m_unlinked, m_total = await _count_unlinked(org_id)
    print(f"\n📊  Vorher:")
    print(f"   Signals:  {s_total} gesamt, {s_unlinked} ohne supplier_id")
    print(f"   Metriken: {m_total} gesamt, {m_unlinked} ohne supplier_id")

    if s_unlinked == 0 and m_unlinked == 0:
        print("\n✅  Alle Datensätze bereits verknüpft — nichts zu tun.")
        return

    print()

    if args.dry_run:
        # Dry-run: rollback statt commit
        async with AsyncSessionFactory() as db:
            async with db.begin():
                sig = await link_signals(org_id, db, min_confidence=args.min_confidence)
                met = await link_metrics(org_id, db, min_confidence=args.min_confidence)
                await db.rollback()  # kein Commit
        print("[DRY-RUN] Kein Commit — Vorschau:")
    else:
        async with AsyncSessionFactory() as db:
            async with db.begin():
                sig = await link_signals(org_id, db, min_confidence=args.min_confidence)
                met = await link_metrics(org_id, db, min_confidence=args.min_confidence)
        print("✅  Commit erfolgreich.")

    print(f"\n📈  Ergebnis:")
    print(f"   Signals:  {sig['linked']} verknüpft / {sig['skipped']} übersprungen / {sig['total']} total")
    print(f"   Metriken: {met['linked']} verknüpft / {met['skipped']} übersprungen / {met['total']} total")

    if not args.dry_run:
        # Nachher-Zustand
        s_unlinked2, _, m_unlinked2, _ = await _count_unlinked(org_id)
        print(f"\n📊  Nachher:")
        print(f"   Signals ohne supplier_id:  {s_unlinked2} (war: {s_unlinked})")
        print(f"   Metriken ohne supplier_id: {m_unlinked2} (war: {m_unlinked})")

        if s_unlinked2 > 0 or m_unlinked2 > 0:
            print(f"\n⚠️  {s_unlinked2 + m_unlinked2} Datensätze nicht verknüpft.")
            print("   Mögliche Ursachen:")
            print("   • company_name weicht stark vom Lieferanten-Namen ab")
            print("   • Lieferant existiert noch nicht in der DB")
            print("   • Confidence unter dem Schwellwert → --min 0.5 versuchen")
            print("   • Alias fehlt → POST /suppliers/{id}/aliases")


if __name__ == "__main__":
    asyncio.run(main())
