"""Widerspruchs-Erkennung — vergleicht Commitments mit tatsächlichen Kennzahlen.

Ablauf je Firma:
  1. Commitment-Signale laden (esg_target_set, commitment, guidance_issued, ...)
  2. Ist-Metriken laden (company_metrics, FY, keine Schätzungen)
  3. LLM (Groq) erkennt Widersprüche zwischen Versprechen und Realität
  4. Erkannte Widersprüche als CompanySignal signal_type="contradiction" speichern
"""
from __future__ import annotations

import json
import uuid

import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.company_intelligence import (
    CompanyMetricModel,
    CompanySignalModel,
)

logger = structlog.get_logger(__name__)

_COMMITMENT_TYPES = {
    "esg_target_set", "commitment", "guidance_issued",
    "climate_commitment", "sustainability_target",
    "net_zero_target", "emissions_reduction_target", "emissions_reduction",
}

_METRIC_LABELS = {
    "revenue": "Umsatz (Mio. €)", "ebitda": "EBITDA (Mio. €)",
    "ebitda_margin": "EBITDA-Marge (%)", "net_income": "Jahresüberschuss (Mio. €)",
    "employees": "Mitarbeiter", "employees_total": "Mitarbeiter gesamt",
    "co2_scope1": "CO₂ Scope 1 (tCO₂)", "co2_scope2": "CO₂ Scope 2 (tCO₂)",
    "co2_scope3": "CO₂ Scope 3 (tCO₂e)", "renewable_energy_pct": "Erneuerbare Energie (%)",
    "women_leadership_pct": "Frauen in Führung (%)", "supplier_audited_pct": "Lieferanten auditiert (%)",
    "esg_score": "ESG-Score", "water_m3": "Wasserverbrauch (m³)",
    "energy_gwh": "Energieverbrauch (GWh)", "roce": "ROCE (%)", "eps": "EPS (€)",
    "debt_ratio": "Verschuldungsgrad (%)",
}

_CONTRADICTION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "commitment_text": {"type": "string"},
            "commitment_year": {"type": "integer"},
            "metric_type": {"type": "string"},
            "expected": {"type": "string"},
            "actual": {"type": "string"},
            "contradiction": {"type": "string"},
            "severity": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["commitment_text", "contradiction", "severity"],
    },
}


def _normalize(name: str) -> str:
    _ALIASES = {
        "bayerische motoren werke aktiengesellschaft": "BMW Group",
        "bmw ag": "BMW Group", "bmw group": "BMW Group", "bmw": "BMW Group",
        "volkswagen ag": "Volkswagen AG", "vw ag": "Volkswagen AG",
        "mercedes-benz group ag": "Mercedes-Benz Group", "daimler ag": "Mercedes-Benz Group",
    }
    return _ALIASES.get(name.strip().lower(), name.strip())


async def _call_llm(prompt: str) -> list[dict]:
    from groq import AsyncGroq
    from shared.config import settings

    client = AsyncGroq(api_key=settings.groq_api_key)
    resp = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist ein ESG-Analyst. Du analysierst ob Unternehmen ihre "
                    "Zusagen und Ziele mit tatsächlichen Kennzahlen einhalten. "
                    "Antworte ausschließlich mit einem JSON-Array. Kein Erklärungstext."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=1500,
        temperature=0,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content or "{}"
    data = json.loads(text)
    # Groq gibt manchmal {"contradictions": [...]} zurück
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    return data if isinstance(data, list) else []


async def detect_contradictions_for_company(
    organization_id: str,
    company_name: str,
    supplier_id: str | None,
    session: AsyncSession,
) -> dict[str, int]:
    """Erkennt Widersprüche zwischen Commitments und Ist-Metriken für eine Firma."""

    # 1. Commitment-Signale laden
    commitment_rows = (await session.execute(
        select(CompanySignalModel).where(
            CompanySignalModel.organization_id == organization_id,
            CompanySignalModel.company_name.ilike(f"%{company_name.split()[0]}%"),
            CompanySignalModel.signal_type.in_(list(_COMMITMENT_TYPES)),
        ).order_by(CompanySignalModel.year.asc())
    )).scalars().all()

    if not commitment_rows:
        return {"contradictions": 0}

    # 2. Ist-Metriken laden (FY, keine Schätzungen)
    metric_rows = (await session.execute(
        select(CompanyMetricModel).where(
            CompanyMetricModel.organization_id == organization_id,
            CompanyMetricModel.company_name.ilike(f"%{company_name.split()[0]}%"),
            CompanyMetricModel.period == "FY",
            CompanyMetricModel.confidence != "estimated",
        ).order_by(CompanyMetricModel.metric_type, CompanyMetricModel.year)
    )).scalars().all()

    if not metric_rows:
        return {"contradictions": 0}

    # 3. Prompt zusammenstellen
    commitments_text = "\n".join(
        f"- [{r.year or '?'}] ({r.signal_type}) {r.description}"
        for r in commitment_rows[:40]  # max 40 Commitments
    )

    # Metriken als kompakte Tabelle: metric_type: year=value, year=value
    metrics_by_type: dict[str, list[str]] = {}
    for m in metric_rows:
        label = _METRIC_LABELS.get(m.metric_type, m.metric_type)
        entry = f"{m.year}={float(m.value):.1f}{m.unit}"
        metrics_by_type.setdefault(label, []).append(entry)

    metrics_text = "\n".join(
        f"- {label}: {', '.join(vals[-8:])}"  # max letzte 8 Jahre
        for label, vals in sorted(metrics_by_type.items())
    )

    prompt = f"""Unternehmen: {company_name}

COMMITMENTS UND ZIELE (aus Geschäftsberichten):
{commitments_text}

TATSÄCHLICHE KENNZAHLEN (Ist-Daten):
{metrics_text}

Finde Widersprüche: Wo wurden Ziele oder Zusagen klar NICHT eingehalten?
Berücksichtige nur prüfbare Widersprüche mit konkreten Zahlen oder klaren Richtungsaussagen.
Ignoriere allgemeine Absichtserklärungen ohne messbare Ziele.

Antworte mit JSON-Objekt: {{"contradictions": [...]}}
Jedes Element:
- commitment_text: Zitat des Commitments
- commitment_year: Jahr in dem das Commitment gemacht wurde (integer)
- metric_type: betroffene Kennzahl (z.B. "co2_scope1", "renewable_energy_pct")
- expected: Was wurde versprochen (kurz)
- actual: Was tatsächlich passiert ist (kurz, mit Zahlen)
- contradiction: Erklärung des Widerspruchs (1 Satz, Deutsch)
- severity: "high" (klarer Verstoß), "medium" (teilweise verfehlt), "low" (Richtung stimmt aber Tempo fehlt)
"""

    try:
        contradictions = await _call_llm(prompt)
    except Exception as exc:
        logger.warning("contradiction_detector.llm_error", company=company_name, error=str(exc))
        return {"contradictions": 0}

    if not contradictions:
        return {"contradictions": 0}

    # 4. Alte Widersprüche löschen und neue schreiben
    await session.execute(
        delete(CompanySignalModel).where(
            CompanySignalModel.organization_id == organization_id,
            CompanySignalModel.company_name.ilike(f"%{company_name.split()[0]}%"),
            CompanySignalModel.signal_type == "contradiction",
        )
    )

    for c in contradictions:
        if not isinstance(c, dict):
            continue
        commitment_text = str(c.get("commitment_text", ""))[:200]
        actual = str(c.get("actual", ""))[:200]
        contradiction_text = str(c.get("contradiction", ""))[:400]
        severity = c.get("severity", "medium")
        if severity not in ("high", "medium", "low"):
            severity = "medium"
        year = c.get("commitment_year")

        description = f"[Commitment] {commitment_text} | [Ist] {actual} | {contradiction_text}"

        # Dimension aus metric_type ableiten
        mt = str(c.get("metric_type", ""))
        dimension = "esg" if any(x in mt for x in ("co2", "energy", "water", "renewable", "esg", "emissions")) else "financial"

        session.add(CompanySignalModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            company_name=company_name,
            supplier_id=supplier_id,
            signal_type="contradiction",
            dimension=dimension,
            direction="negative",
            severity=severity,
            description=description,
            year=int(year) if year else None,
            source_doc_id=None,
        ))

    logger.info(
        "contradiction_detector.done",
        company=company_name,
        found=len(contradictions),
    )
    return {"contradictions": len(contradictions)}


async def detect_all_contradictions(
    organization_id: str,
    session: AsyncSession,
) -> dict[str, int]:
    """Führt Widerspruchserkennung für alle Firmen in der Organisation durch."""
    # Einzigartige Firmennamen aus Commitments
    from sqlalchemy import func
    company_rows = (await session.execute(
        select(CompanySignalModel.company_name, CompanySignalModel.supplier_id)
        .where(
            CompanySignalModel.organization_id == organization_id,
            CompanySignalModel.signal_type.in_(list(_COMMITMENT_TYPES)),
        )
        .group_by(CompanySignalModel.company_name, CompanySignalModel.supplier_id)
    )).all()

    total = 0
    for row in company_rows:
        result = await detect_contradictions_for_company(
            organization_id=organization_id,
            company_name=row.company_name,
            supplier_id=row.supplier_id,
            session=session,
        )
        total += result.get("contradictions", 0)

    return {"total_contradictions": total, "companies_checked": len(company_rows)}
