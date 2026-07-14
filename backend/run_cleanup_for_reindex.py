"""
Cleanup script — entfernt alte Dokument-Chunks und Datei-Einträge
damit alle 24 Dokumente neu hochgeladen und mit Docling re-indexiert werden können.

Was wird gelöscht:
  - rag_documents    → alle 13.987 alten Chunks (werden nach Re-Upload neu erstellt)
  - document_files   → alle 24 Einträge (werden nach Re-Upload neu erstellt)

Was wird BEHALTEN:
  - company_metrics  → 329 extrahierte Kennzahlen (wertvolle Intelligenz)
  - company_signals  → 530 extrahierte Signale (wertvolle Intelligenz)
  - document_sources → Upload-Quellen (werden für Re-Upload benötigt)

source_doc_id in metrics/signals wird auf NULL gesetzt (FK-Konflikt vermeiden).

Usage:
    python run_cleanup_for_reindex.py [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from infrastructure.persistence.database import AsyncSessionFactory


async def main(dry_run: bool):
    async with AsyncSessionFactory() as session:

        # ── Vorher: Zählen ────────────────────────────────────────────────────
        counts = {}
        for table in ["rag_documents", "document_files", "company_metrics", "company_signals"]:
            r = await session.execute(text(f"SELECT count(*) FROM {table}"))
            counts[table] = r.scalar()

        print("\n=== EIOS Re-Index Cleanup ===\n")
        print("Aktueller Stand:")
        print(f"  rag_documents   : {counts['rag_documents']:>6}  → wird GELÖSCHT")
        print(f"  document_files  : {counts['document_files']:>6}  → wird GELÖSCHT")
        print(f"  company_metrics : {counts['company_metrics']:>6}  → wird BEHALTEN (source_doc_id → NULL)")
        print(f"  company_signals : {counts['company_signals']:>6}  → wird BEHALTEN (source_doc_id → NULL)")

        if dry_run:
            print("\nDRY RUN — keine Änderungen vorgenommen.")
            return

        print("\nBereinigung läuft...")

        # 1. source_doc_id nullifizieren (FK-Konflikt vermeiden)
        r = await session.execute(text("UPDATE company_metrics SET source_doc_id = NULL WHERE source_doc_id IS NOT NULL"))
        print(f"  ✓ company_metrics.source_doc_id → NULL  ({r.rowcount} Zeilen)")

        r = await session.execute(text("UPDATE company_signals SET source_doc_id = NULL WHERE source_doc_id IS NOT NULL"))
        print(f"  ✓ company_signals.source_doc_id → NULL  ({r.rowcount} Zeilen)")

        # 2. Alle rag_documents löschen
        r = await session.execute(text("DELETE FROM rag_documents"))
        print(f"  ✓ rag_documents gelöscht           ({r.rowcount} Zeilen)")

        # 3. Alle document_files löschen
        r = await session.execute(text("DELETE FROM document_files"))
        print(f"  ✓ document_files gelöscht          ({r.rowcount} Zeilen)")

        await session.commit()

        # ── Nachher: Verifizieren ─────────────────────────────────────────────
        print("\nVerifikation:")
        for table in ["rag_documents", "document_files", "company_metrics", "company_signals"]:
            r = await session.execute(text(f"SELECT count(*) FROM {table}"))
            print(f"  {table:<20}: {r.scalar()}")

        print("\n✅ Bereinigung abgeschlossen.")
        print("\nNächste Schritte:")
        print("  1. Gehe zu EIOS → Dokumente")
        print("  2. Lade alle 24 PDFs erneut hoch")
        print("  3. Docling verarbeitet sie automatisch mit Tabellen + semantischem Chunking")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
