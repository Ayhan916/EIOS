"""Cross-Source Intelligence Analyzer.

Verknüpft eingehende Signale (News, Widersprüche, YoY-Alerts) mit den
Lieferanten des Nutzers über NACE-Code-Verwandtschaft.

Logik:
  1. Triggerunternehmen → NACE-Code ermitteln
  2. Betroffene NACE-Codes ableiten (gleicher Sektor + typische Upstream-Lieferanten)
  3. Lieferanten des Nutzers in diesen NACE-Codes finden
  4. LLM synthesisiert Auswirkung + Handlungsempfehlung
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# ── NACE-Abhängigkeits-Graph ──────────────────────────────────────────────────
# Schlüssel = betroffene Branche → Werte = typische Upstream-Lieferanten-Branchen
# Quelle: Eurostat Input-Output-Tabellen, vereinfacht

_NACE_UPSTREAM: dict[str, list[str]] = {
    "C29": ["C27", "C26", "C24", "C25", "C22", "C20", "B07", "H49", "C17"],
    # Automobil → Elektronik, Halbleiter, Stahl, Metallteile, Gummi, Chemie, Bergbau, Logistik, Verpackung
    "C27": ["C26", "C24", "C25", "B07", "C20"],
    # Elektrische Ausrüstung → Halbleiter, Stahl, Metallteile, Bergbau, Chemie
    "C26": ["B07", "C24", "C20", "C21"],
    # Halbleiter/Elektronik → Bergbau, Stahl, Chemie, Pharma-Grundstoffe
    "C24": ["B05", "B07", "B08", "D35"],
    # Stahl → Kohle, Metallerzbergbau, Steinbruch, Energie
    "C28": ["C24", "C25", "C26", "C27"],
    # Maschinenbau → Stahl, Metallteile, Elektronik, Elektrische Ausrüstung
    "C30": ["C27", "C26", "C24", "C29"],
    # Sonstiger Fahrzeugbau (Luft/Bahn) → Elektronik, Halbleiter, Stahl, Automobil-Zulieferer
    "G46": ["C10", "C20", "C24", "H49"],
    # Großhandel → Lebensmittel, Chemie, Stahl, Logistik
    "H49": ["C19", "D35", "G47"],
    # Landtransport → Mineralöl, Energie, Einzelhandel
    "D35": ["B05", "B06", "C19"],
    # Energie → Kohle, Öl/Gas, Mineralölverarbeitung
}

# Gleiche Hauptgruppe (erste 3 Zeichen gleich) = direkter Sektor-Stress
def _same_sector(nace_a: str, nace_b: str) -> bool:
    return nace_a[:3] == nace_b[:3]


def _get_related_nace(trigger_nace: str) -> dict[str, str]:
    """Gibt alle betroffenen NACE-Codes mit Beziehungstyp zurück."""
    related: dict[str, str] = {}

    # Gleicher Sektor → Sektor-Stress
    related[trigger_nace] = "sector_stress"

    # Upstream-Lieferanten → Upstream-Druck
    for upstream in _NACE_UPSTREAM.get(trigger_nace, []):
        related[upstream] = "upstream_pressure"

    # Wer beliefert den Trigger-Sektor? → Downstream-Risiko für deren Abnehmer
    for sector, upstreams in _NACE_UPSTREAM.items():
        if trigger_nace in upstreams and sector != trigger_nace:
            if sector not in related:
                related[sector] = "downstream_risk"

    return related


# ── Impact-Klassifikation ─────────────────────────────────────────────────────

_SIGNAL_SEVERITY_MAP = {
    "contradiction": "medium",
    "yoy_comparison": "low",
    "plant_closure": "critical",
    "layoffs": "high",
    "restructuring": "medium",
    "insolvency_risk": "critical",
    "rating_downgrade": "high",
    "supply_chain_disruption": "critical",
    "esg_controversy": "medium",
    "legal_action": "high",
    "acquisition": "low",
    "esg_target_missed": "medium",
}

_IMPACT_TYPE_MAP = {
    "plant_closure": "supply_disruption",
    "insolvency_risk": "supply_loss",
    "layoffs": "capacity_reduction",
    "restructuring": "delivery_risk",
    "rating_downgrade": "financial_contagion",
    "supply_chain_disruption": "supply_disruption",
    "esg_controversy": "reputational_spillover",
    "esg_target_missed": "regulatory_spillover",
    "contradiction": "commitment_risk",
    "yoy_comparison": "trend_risk",
    "legal_action": "regulatory_spillover",
}


# ── LLM-Synthese ─────────────────────────────────────────────────────────────

async def _synthesize(
    trigger_company: str,
    trigger_signal_type: str,
    trigger_description: str,
    affected_suppliers: list[dict],
    impact_type: str,
    severity: str,
) -> dict:
    """LLM erzeugt Begründung und Handlungsempfehlungen."""
    from infrastructure.llm.deps import get_extraction_llm_provider
    from application.ports.llm import Message

    supplier_list = "\n".join(
        f"  - {s['name']} ({s['nace_code']}, {s['relation']})"
        for s in affected_suppliers[:10]
    )

    prompt = f"""Analyze this cross-source supply chain risk and return JSON.

Trigger event:
  Company: {trigger_company}
  Signal: {trigger_signal_type}
  Description: {trigger_description[:400]}

Affected suppliers in the user's supply chain:
{supplier_list if supplier_list else "  (none directly identified — sector-level exposure)"}

Impact type: {impact_type}
Preliminary severity: {severity}

Return ONLY valid JSON:
{{
  "reasoning": "2-3 sentences explaining WHY this event affects the user's supply chain, referencing specific NACE sectors and mechanisms",
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "severity": "{severity}"
}}

Be concrete. Reference the actual companies and sectors. Keep reasoning under 150 words."""

    llm = get_extraction_llm_provider()
    try:
        resp = await llm.complete(
            messages=[Message(role="user", content=prompt)],
            system="You are a supply chain risk analyst. Return only valid JSON.",
            max_tokens=512,
            temperature=0.0,
        )
        raw = resp.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as exc:
        logger.warning("cross_source.llm_failed", error=str(exc))
        return {
            "reasoning": f"{trigger_company} ({trigger_signal_type}) betrifft Sektoren in deiner Lieferkette über NACE-Code-Verwandtschaft.",
            "recommended_actions": ["Lieferanten-Status prüfen", "Alternativlieferanten evaluieren", "Monitoring intensivieren"],
            "severity": severity,
        }


# ── Haupt-Analyse-Funktion ────────────────────────────────────────────────────

async def analyze_cross_impact(
    organization_id: str,
    trigger_company: str,
    trigger_nace: str | None,
    trigger_signal_type: str,
    trigger_description: str,
    trigger_signal_id: str | None,
    session: AsyncSession,
) -> dict:
    """Führt die Cross-Source-Analyse durch und speichert einen Alert."""

    if not trigger_nace:
        # NACE aus Lieferanten-DB ermitteln
        row = (await session.execute(
            text("SELECT nace_code FROM suppliers WHERE LOWER(name) LIKE :name AND organization_id = :org LIMIT 1"),
            {"name": f"%{trigger_company.lower()[:20]}%", "org": organization_id},
        )).fetchone()
        trigger_nace = row[0] if row else None

    # Betroffene NACE-Codes berechnen
    related_nace = _get_related_nace(trigger_nace) if trigger_nace else {}

    # Lieferanten des Nutzers in betroffenen NACE-Codes finden
    affected_suppliers: list[dict] = []
    if related_nace:
        nace_list = list(related_nace.keys())
        rows = (await session.execute(
            text("""
                SELECT id, name, nace_code, country, supplier_tier
                FROM suppliers
                WHERE organization_id = :org
                  AND nace_code = ANY(:nace_list)
                  AND supplier_status = 'Active'
                ORDER BY supplier_tier, name
            """),
            {"org": organization_id, "nace_list": nace_list},
        )).fetchall()

        for r in rows:
            nace = r[2] or ""
            relation = related_nace.get(nace, "indirect")
            affected_suppliers.append({
                "id": str(r[0]),
                "name": r[1],
                "nace_code": nace,
                "country": r[3],
                "supplier_tier": r[4],
                "relation": relation,
            })

    # Severity + Impact-Typ
    base_severity = _SIGNAL_SEVERITY_MAP.get(trigger_signal_type, "medium")
    impact_type = _IMPACT_TYPE_MAP.get(trigger_signal_type, "sector_risk")

    # Severity erhöhen wenn direkte Lieferanten betroffen
    direct_hits = [s for s in affected_suppliers if s["relation"] == "sector_stress"]
    if direct_hits and base_severity == "low":
        base_severity = "medium"
    elif direct_hits and base_severity == "medium":
        base_severity = "high"

    # LLM-Synthese
    synthesis = await _synthesize(
        trigger_company=trigger_company,
        trigger_signal_type=trigger_signal_type,
        trigger_description=trigger_description,
        affected_suppliers=affected_suppliers,
        impact_type=impact_type,
        severity=base_severity,
    )

    severity = synthesis.get("severity", base_severity)
    reasoning = synthesis.get("reasoning", "")
    actions = synthesis.get("recommended_actions", [])

    # Alert speichern
    alert_id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO cross_source_alerts
              (id, organization_id, trigger_signal_id, trigger_company, trigger_nace,
               trigger_signal_type, trigger_description, impact_type, severity,
               affected_nace_codes, affected_suppliers, reasoning, recommended_actions,
               status, created_at)
            VALUES
              (:id, :org, :sig_id, :company, :nace,
               :sig_type, :description, :impact_type, :severity,
               :nace_codes, :suppliers, :reasoning, :actions,
               'open', :now)
        """),
        {
            "id": alert_id,
            "org": organization_id,
            "sig_id": trigger_signal_id,
            "company": trigger_company,
            "nace": trigger_nace,
            "sig_type": trigger_signal_type,
            "description": trigger_description[:1000],
            "impact_type": impact_type,
            "severity": severity,
            "nace_codes": json.dumps(related_nace),
            "suppliers": json.dumps(affected_suppliers),
            "reasoning": reasoning,
            "actions": json.dumps(actions),
            "now": datetime.now(UTC),
        },
    )
    await session.flush()

    logger.info(
        "cross_source.alert_created",
        alert_id=alert_id,
        trigger=trigger_company,
        nace=trigger_nace,
        affected_count=len(affected_suppliers),
        severity=severity,
    )

    return {
        "alert_id": alert_id,
        "trigger_company": trigger_company,
        "trigger_nace": trigger_nace,
        "impact_type": impact_type,
        "severity": severity,
        "affected_nace_codes": related_nace,
        "affected_suppliers": affected_suppliers,
        "reasoning": reasoning,
        "recommended_actions": actions,
    }
