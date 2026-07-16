"""Trend-Analyzer — erkennt signifikante Muster in company_metrics Zeitreihen.

Erkannte Muster:
  - Konsekutiver Trend: 2+ aufeinanderfolgende Jahre gleiche Richtung
  - Großer Einzeljahres-Sprung: >20% Veränderung in einem Jahr
  - ESG-Alarmierung: CO2/Wasser steigt, Erneuerbarer-Anteil sinkt
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Firma-Name-Normalisierung: bekannte Varianten → kanonischer Name
_COMPANY_ALIASES: dict[str, str] = {
    "bayerische motoren werke aktiengesellschaft": "BMW Group",
    "bayerische motoren werke ag":                "BMW Group",
    "bmw ag":                                     "BMW Group",
    "bmw group":                                  "BMW Group",
    "bmw":                                        "BMW Group",
    "volkswagen ag":                              "Volkswagen AG",
    "volkswagen group":                           "Volkswagen AG",
    "vw ag":                                      "Volkswagen AG",
    "mercedes-benz group ag":                     "Mercedes-Benz Group",
    "mercedes benz group ag":                     "Mercedes-Benz Group",
    "daimler ag":                                 "Mercedes-Benz Group",
    "siemens ag":                                 "Siemens AG",
    "basf se":                                    "BASF SE",
    "sap se":                                     "SAP SE",
}


def _normalize_company(name: str) -> str:
    return _COMPANY_ALIASES.get(name.strip().lower(), name.strip())


# Metriken wo höher = besser
_HIGHER_BETTER = {
    "revenue", "ebitda", "ebitda_margin", "net_income", "free_cashflow",
    "renewable_energy_pct", "women_leadership_pct", "supplier_audited_pct",
    "esg_score", "roce", "eps",
}

# Metriken wo niedriger = besser
_LOWER_BETTER = {
    "co2_scope1", "co2_scope2", "co2_scope3",
    "water_m3", "debt_ratio", "lost_time_injury_rate",
}


def _is_concerning(metric_type: str, direction: str) -> bool:
    """Ist diese Trendrichtung besorgniserregend?"""
    if metric_type in _HIGHER_BETTER:
        return direction == "down"
    if metric_type in _LOWER_BETTER:
        return direction == "up"
    return False


def _is_positive(metric_type: str, direction: str) -> bool:
    """Ist diese Trendrichtung positiv?"""
    if metric_type in _HIGHER_BETTER:
        return direction == "up"
    if metric_type in _LOWER_BETTER:
        return direction == "down"
    return False


@dataclass
class YearChange:
    year_from: int
    year_to: int
    value_from: float
    value_to: float
    pct_change: float
    unit: str


@dataclass
class TrendAlert:
    company_name: str
    metric_type: str
    unit: str
    alert_type: str          # "consecutive" | "spike"
    direction: str           # "up" | "down"
    sentiment: str           # "positive" | "negative" | "neutral"
    severity: str            # "critical" | "high" | "medium" | "low"
    year_start: int
    year_end: int
    avg_pct_change: float
    changes: list[YearChange] = field(default_factory=list)
    description: str = ""
    reference_source: str | None = None
    reference_url: str | None = None
    verification_note: str | None = None


def analyze_trends(
    metrics: list,
    min_consecutive: int = 2,
    spike_threshold: float = 20.0,
) -> list[TrendAlert]:
    """Analysiert Metriken auf Trends und gibt Alert-Liste zurück.

    Args:
        metrics: Liste von CompanyMetricModel-Objekten (oder dicts mit gleichen Feldern).
        min_consecutive: Mindestanzahl aufeinanderfolgender Jahre für konsekutiven Trend.
        spike_threshold: Prozentualer Schwellenwert für Einzeljahres-Sprung.
    """
    def _get(obj, attr, default=""):
        v = getattr(obj, attr, None)
        return v if v is not None else default

    # Gruppieren nach (normalized_company_name, metric_type, period)
    # Schließe geschätzte/forecast Werte aus (confidence="estimated")
    groups: dict[tuple, list] = {}
    for m in metrics:
        if _get(m, "confidence", "") == "estimated":
            continue
        canonical = _normalize_company(_get(m, "company_name") or "")
        key = (
            canonical,
            _get(m, "metric_type") or "",
            _get(m, "period") or "FY",
        )
        groups.setdefault(key, []).append(m)

    alerts: list[TrendAlert] = []

    for (company, metric_type, period), ms in groups.items():  # company is already normalized
        if period != "FY":
            continue  # Nur Jahreswerte (keine Quartale)

        # Sortieren nach Jahr
        ms_sorted = sorted(ms, key=lambda x: _get(x, "year", 0) or 0)
        if len(ms_sorted) < 2:
            continue

        # Nur vergleichen wenn alle Datenpunkte dieselbe Einheit haben
        units = {_get(m, "unit", "") for m in ms_sorted}
        if len(units) > 1:
            continue

        # Verifizierte Ausreißer (discrepant) entfernen
        def _is_discrepant(m) -> bool:
            if not _get(m, "is_verified", False):
                return False
            ref = _get(m, "reference_value", None)
            if ref is None:
                return False
            val = float(_get(m, "value", 0) or 0)
            ref_f = float(ref)
            return ref_f != 0 and abs(val) > 5 * abs(ref_f)

        ms_sorted = [m for m in ms_sorted if not _is_discrepant(m)]
        if len(ms_sorted) < 2:
            continue

        # Jahr-zu-Jahr-Veränderungen berechnen
        changes: list[YearChange] = []
        for i in range(1, len(ms_sorted)):
            prev = ms_sorted[i - 1]
            curr = ms_sorted[i]

            v_prev = float(_get(prev, "value", 0) or 0)
            v_curr = float(_get(curr, "value", 0) or 0)
            unit = _get(curr, "unit", "")
            y_prev = int(_get(prev, "year", 0) or 0)
            y_curr = int(_get(curr, "year", 0) or 0)

            if abs(v_prev) < 1e-9:
                continue

            pct = (v_curr - v_prev) / abs(v_prev) * 100.0
            changes.append(YearChange(
                year_from=y_prev,
                year_to=y_curr,
                value_from=v_prev,
                value_to=v_curr,
                pct_change=round(pct, 1),
                unit=unit,
            ))

        if not changes:
            continue

        unit = changes[-1].unit

        # Quellen-Info aus dem letzten verifizierten Datenpunkt
        ref_source = None
        ref_url = None
        ref_note = None
        for m in reversed(ms_sorted):
            if _get(m, "is_verified", False) and _get(m, "reference_source"):
                ref_source = _get(m, "reference_source")
                ref_url = _get(m, "reference_url")
                ref_note = _get(m, "verification_note")
                break

        # ── Konsekutiver Trend ────────────────────────────────────────────
        # Suche längste aufeinanderfolgende Sequenz gleicher Richtung
        def _find_sequences(chg_list: list[YearChange]) -> list[list[YearChange]]:
            seqs = []
            i = 0
            while i < len(chg_list):
                direction = "up" if chg_list[i].pct_change > 0 else "down"
                seq = [chg_list[i]]
                j = i + 1
                while j < len(chg_list):
                    d = "up" if chg_list[j].pct_change > 0 else "down"
                    if d == direction:
                        seq.append(chg_list[j])
                        j += 1
                    else:
                        break
                if len(seq) >= min_consecutive:
                    seqs.append(seq)
                i = j if j > i + 1 else i + 1
            return seqs

        for seq in _find_sequences(changes):
            direction = "up" if seq[0].pct_change > 0 else "down"
            avg_pct = sum(abs(c.pct_change) for c in seq) / len(seq)
            n_years = len(seq)

            # Severity
            if n_years >= 3 and avg_pct >= 15:
                severity = "critical"
            elif n_years >= 3 or (n_years >= 2 and avg_pct >= 10):
                severity = "high"
            elif avg_pct >= 5:
                severity = "medium"
            else:
                severity = "low"

            sentiment = (
                "positive" if _is_positive(metric_type, direction)
                else "negative" if _is_concerning(metric_type, direction)
                else "neutral"
            )

            sign = "+" if direction == "up" else "-"
            description = (
                f"{n_years} aufeinanderfolgende Jahre "
                f"{sign}{avg_pct:.1f}% Ø ({seq[0].year_from}→{seq[-1].year_to})"
            )

            alerts.append(TrendAlert(
                company_name=company,
                metric_type=metric_type,
                unit=unit,
                alert_type="consecutive",
                direction=direction,
                sentiment=sentiment,
                severity=severity,
                year_start=seq[0].year_from,
                year_end=seq[-1].year_to,
                avg_pct_change=round(avg_pct, 1),
                changes=seq,
                description=description,
                reference_source=ref_source,
                reference_url=ref_url,
                verification_note=ref_note,
            ))

        # ── Großer Einzeljahres-Sprung (letzter Datenpunkt) ───────────────
        last = changes[-1]
        if abs(last.pct_change) >= spike_threshold:
            direction = "up" if last.pct_change > 0 else "down"
            severity = "high" if abs(last.pct_change) >= 30 else "medium"
            sentiment = (
                "positive" if _is_positive(metric_type, direction)
                else "negative" if _is_concerning(metric_type, direction)
                else "neutral"
            )
            sign = "+" if last.pct_change > 0 else ""
            description = (
                f"Sprung {sign}{last.pct_change:.1f}% "
                f"({last.year_from}→{last.year_to})"
            )
            alerts.append(TrendAlert(
                company_name=company,
                metric_type=metric_type,
                unit=unit,
                alert_type="spike",
                direction=direction,
                sentiment=sentiment,
                severity=severity,
                year_start=last.year_from,
                year_end=last.year_to,
                avg_pct_change=abs(last.pct_change),
                changes=[last],
                description=description,
                reference_source=ref_source,
                reference_url=ref_url,
                verification_note=ref_note,
            ))

    # Sortierung: negative Sentiment zuerst, dann Severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sentiment_order = {"negative": 0, "neutral": 1, "positive": 2}
    alerts.sort(key=lambda a: (
        sentiment_order.get(a.sentiment, 9),
        severity_order.get(a.severity, 9),
        a.company_name,
    ))

    return alerts
