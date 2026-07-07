"""RAG-enhanced Scenario Simulator — Phase 3.

Hybrides Modell:
  1. Deterministisch  — SimulationEngine: NACE × ScenarioType → CSDDD-Wahrscheinlichkeiten
  2. RAG-enhanced     — semantische Suche nach historischen Parallelen → LLM-Narrativ

Der deterministische Teil (M43-konform) bleibt unverändert.
Der LLM-Teil ist rein narrativ und ersetzt keine menschliche Entscheidung.
"""

from __future__ import annotations

import re
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .retrieval import retrieve

logger = structlog.get_logger(__name__)

# Szenario-Suchbegriffe für RAG-Retrieval (DE + EN)
_SCENARIO_QUERIES: dict[str, str] = {
    "geopolitical_conflict": "geopolitischer Konflikt Krieg Sanktionen Lieferkette supply chain conflict war",
    "sanctions_escalation":  "Sanktionen Embargo OFAC blacklist sanctions escalation",
    "natural_disaster":      "Naturkatastrophe Überschwemmung Erdbeben flood earthquake disaster supply chain",
    "regulatory_change":     "Regulierung CSDDD LkSG Compliance neue Vorschriften regulatory change",
    "labour_unrest":         "Streik Arbeitskampf Gewerkschaft workers strike labour unrest",
    "supply_shortage":       "Lieferengpass Rohstoffknappheit Halbleiter shortage supply disruption chip",
}

_SCENARIO_DISPLAY: dict[str, str] = {
    "geopolitical_conflict": "Geopolitischer Konflikt",
    "sanctions_escalation":  "Sanktionsverschärfung",
    "natural_disaster":      "Naturkatastrophe",
    "regulatory_change":     "Regulatorische Verschärfung",
    "labour_unrest":         "Arbeitskampf / Streik",
    "supply_shortage":       "Rohstoff- / Lieferengpass",
}

_RIGHT_LABELS: dict[str, str] = {
    "child_labour":           "Kinderarbeit",
    "forced_labour":          "Zwangsarbeit",
    "freedom_of_association": "Vereinigungsfreiheit",
    "collective_bargaining":  "Tarifverhandlungen",
    "discrimination":         "Diskriminierungsverbot",
    "minimum_wage":           "Mindestlohn",
    "working_hours":          "Arbeitszeiten",
    "occupational_safety":    "Arbeitssicherheit",
    "land_rights":            "Landrechte",
    "water_rights":           "Wasserrechte",
    "environmental_destruction": "Umweltzerstörung",
    "harmful_chemicals":      "Schadstoffe / Chemikalien",
    "biodiversity":           "Biodiversität",
    "mercury":                "Quecksilber",
    "hazardous_waste":        "Gefährliche Abfälle",
    "privacy":                "Datenschutz / Privatsphäre",
    "freedom_of_expression":  "Meinungsfreiheit",
    "human_dignity":          "Menschenwürde",
    "modern_slavery":         "Moderne Sklaverei",
    "migrant_worker_rights":  "Wanderarbeiterrechte",
    "community_rights":       "Gemeinschaftsrechte",
}

_SYSTEM_PROMPT = """Du bist ein spezialisierter Lieferketten-Risikostratege für EIOS.
Du analysierst die Auswirkungen von Szenarien auf konkrete Lieferanten und erstellst
handlungsorientierte Risikonarrative auf Basis deterministischer Scores und historischer Belege.

Regeln:
- Antworte IMMER auf Deutsch
- Beziehe dich auf die bereitgestellten CSDDD-Risikowerte und Quelltexte
- Sei konkret und lieferantenspezifisch — kein generisches Boilerplate
- Nenne die 2-3 kritischsten betroffenen CSDDD-Rechte beim Namen
- Schliesse mit 3 konkreten, priorisierten Handlungsempfehlungen
- Formatiere übersichtlich mit Abschnitten"""


async def _get_supplier_info(supplier_id: str, session: AsyncSession) -> dict:
    from infrastructure.persistence.models.supplier import SupplierModel
    result = await session.execute(
        select(
            SupplierModel.nace_code,
            SupplierModel.supplier_type,
            SupplierModel.commodity_code,
        ).where(SupplierModel.id == supplier_id)
    )
    row = result.one_or_none()
    if row is None:
        return {"nace_code": None, "supplier_type": "manufacturing", "commodity_code": None}
    return {"nace_code": row[0], "supplier_type": row[1] or "manufacturing", "commodity_code": row[2]}


async def simulate(
    scenario_type: str,
    organization_id: str,
    session: AsyncSession,
    supplier_id: str,
    supplier_name: str,
) -> dict:
    """Führt eine hybride Szenario-Simulation durch.

    Gibt zurück:
      narrative           — LLM-Narrativ (supplier-spezifisch, DE)
      top_affected_rights — Top-5 betroffene CSDDD-Rechte mit Delta
      deterministic_ok    — ob deterministischer Teil verfügbar war
      sources             — verwendete RAG-Quellen
      chunks_found        — Anzahl relevanter Quellen
      model               — LLM-Modell
    """
    # ── 1. Deterministischer Teil ─────────────────────────────────────────────
    top_rights: list[dict] = []
    scenario_name = _SCENARIO_DISPLAY.get(scenario_type, scenario_type)
    deterministic_ok = False

    try:
        supplier_info = await _get_supplier_info(supplier_id, session)
        is_commodity = supplier_info["supplier_type"] == "commodity"
        commodity_code = supplier_info["commodity_code"]

        if is_commodity and commodity_code:
            # Rohstofflieferant → CommodityRiskMatrix
            from application.rag.commodity_risk_matrix import simulate_commodity
            sim = simulate_commodity(commodity_code, scenario_type)
            sorted_rights = sorted(sim.delta.items(), key=lambda x: x[1], reverse=True)
            for right_id, delta in sorted_rights[:5]:
                if delta > 0:
                    top_rights.append({
                        "right_id":   right_id,
                        "right_name": _RIGHT_LABELS.get(right_id, right_id),
                        "baseline":   sim.baseline_scores[right_id],
                        "adjusted":   sim.scenario_scores[right_id],
                        "delta":      delta,
                    })
            deterministic_ok = True

        else:
            # Fertigungslieferant → SimulationEngine (NACE × Szenario)
            from application.sector_intelligence.simulation_engine import SimulationEngine
            from domain.enums import CSDDDRight, ScenarioType

            nace_code = supplier_info["nace_code"]
            if nace_code:
                _m = re.search(r'(\d{2})', nace_code)
                clean_nace = _m.group(1) if _m else nace_code
                engine = SimulationEngine()
                result = engine.simulate(clean_nace, ScenarioType(scenario_type))
                scenario_name = result.scenario_name

                sorted_rights = sorted(result.delta.items(), key=lambda x: x[1], reverse=True)
                for right, delta in sorted_rights[:5]:
                    if delta > 0:
                        top_rights.append({
                            "right_id":   right.value,
                            "right_name": _RIGHT_LABELS.get(right.value, right.value),
                            "baseline":   result.baseline_scores[right],
                            "adjusted":   result.scenario_scores[right],
                            "delta":      delta,
                        })
                deterministic_ok = True

    except Exception as exc:
        logger.warning("rag_simulate.deterministic_failed", error=str(exc))

    # ── 2. RAG-Retrieval ──────────────────────────────────────────────────────
    rag_query = f"{supplier_name} {_SCENARIO_QUERIES.get(scenario_type, scenario_type)}"
    chunks = await retrieve(
        query=rag_query,
        organization_id=organization_id,
        session=session,
        supplier_id=supplier_id,
        top_k=5,
        min_similarity=0.20,
    )
    # Falls supplier-spezifisch zu wenig Treffer: breiter suchen
    if len(chunks) < 2:
        broad = await retrieve(
            query=_SCENARIO_QUERIES.get(scenario_type, scenario_type),
            organization_id=organization_id,
            session=session,
            top_k=4,
            min_similarity=0.20,
        )
        seen = {c["id"] for c in chunks}
        chunks += [c for c in broad if c["id"] not in seen][:3]

    # ── 3. Prompt aufbauen ────────────────────────────────────────────────────
    rights_text = ""
    if top_rights:
        rights_text = "\n\nDeterministischer CSDDD-Impact (Top betroffene Rechte):\n"
        for r in top_rights:
            rights_text += (
                f"  • {r['right_name']}: {r['baseline']} → {r['adjusted']} "
                f"(+{r['delta']} Punkte)\n"
            )

    context_text = ""
    if chunks:
        context_text = "\n\nHistorische Belege aus dem Knowledge Base:\n"
        for i, c in enumerate(chunks, 1):
            meta = []
            if c.get("doc_type") == "news_article":
                meta.append("Nachricht")
            elif c.get("doc_type") == "intelligence_event":
                meta.append("Intelligence-Event")
            if c.get("published_at"):
                meta.append(c["published_at"][:10])
            context_text += f"[{i}] {' | '.join(meta)}\n{c['content']}\n\n"

    user_prompt = (
        f"Lieferant: {supplier_name}\n"
        f"Szenario: {scenario_name} ({scenario_type})\n"
        f"{rights_text}"
        f"{context_text}"
        f"\nErstelle eine strukturierte Risikoanalyse für dieses Szenario. "
        f"Beantworte: (1) Welche konkreten Auswirkungen hat dieses Szenario auf {supplier_name}? "
        f"(2) Welche CSDDD-Rechte sind am stärksten betroffen und warum? "
        f"(3) Welche 3 Massnahmen sollten sofort eingeleitet werden?"
    )

    # ── 4. LLM-Narrativ ───────────────────────────────────────────────────────
    narrative = ""
    model_used = "unbekannt"
    try:
        from application.ports.llm import Message
        from infrastructure.llm.deps import get_llm_provider

        llm = get_llm_provider()
        model_used = llm.model_name()
        response = await llm.complete(
            messages=[Message(role="user", content=user_prompt)],
            system=_SYSTEM_PROMPT,
            max_tokens=1200,
            temperature=0.15,
        )
        narrative = response.content.strip()
    except Exception as exc:
        logger.warning("rag_simulate.llm_failed", error=str(exc))
        narrative = (
            f"LLM nicht verfügbar. Deterministischer Impact:\n"
            + "\n".join(f"• {r['right_name']}: +{r['delta']}" for r in top_rights)
        )

    sources = [
        {
            "rank":            i + 1,
            "doc_type":        c["doc_type"],
            "content_preview": c["content"][:120] + "…" if len(c["content"]) > 120 else c["content"],
            "severity":        c.get("severity"),
            "source_name":     c.get("source_name"),
            "published_at":    c.get("published_at", "")[:10] if c.get("published_at") else None,
            "similarity":      c["similarity"],
        }
        for i, c in enumerate(chunks)
    ]

    logger.info(
        "rag_simulate.done",
        org=organization_id,
        supplier_id=supplier_id,
        scenario=scenario_type,
        chunks=len(chunks),
        rights=len(top_rights),
        model=model_used,
    )

    return {
        "scenario_type":        scenario_type,
        "scenario_name":        scenario_name,
        "supplier_name":        supplier_name,
        "narrative":            narrative,
        "top_affected_rights":  top_rights,
        "deterministic_ok":     deterministic_ok,
        "sources":              sources,
        "chunks_found":         len(chunks),
        "model":                model_used,
    }
