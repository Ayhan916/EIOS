"""Sustainability Scorecards, Forecasting, and Scenario Analysis.

All scoring is deterministic and transparent — no ML, no LLMs.
Scoring formula:
  - environmental_score = avg(ENVIRONMENTAL KPI attainment %)
  - social_score = avg(SOCIAL KPI attainment %)
  - governance_score = avg(GOVERNANCE KPI attainment %)
  - overall_score = weighted average (40% E, 30% S, 30% G)

Forecasting methods:
  - LINEAR_TREND: linear regression over historical data points
  - MOVING_AVERAGE: simple moving average over window
"""

from __future__ import annotations

import uuid
from datetime import datetime
from statistics import mean

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.sustainability import (
    FORECAST_METHODS,
    FORECAST_TYPES,
    SCENARIO_TYPES,
    ESGKPIModel,
    KPIMeasurementModel,
    PerformanceForecastModel,
    ScenarioAnalysisModel,
    SustainabilityScorecardModel,
)

from .objective_service import SustainabilityError, _now

_ENV_WEIGHT = 0.40
_SOC_WEIGHT = 0.30
_GOV_WEIGHT = 0.30


def _kpi_attainment(measured: float, target: float) -> float:
    """Attainment as percent (capped 0-100). Handles zero-target edge case."""
    if target == 0:
        return 100.0 if measured == 0 else 0.0
    return max(0.0, min(100.0, round(measured / target * 100, 2)))


def compute_scorecard(
    organization_id: str,
    period_start: datetime,
    period_end: datetime,
    actor_id: str,
    session: Session,
) -> SustainabilityScorecardModel:
    """Compute scorecard from KPI measurements in the given period."""
    kpis = (
        session.query(ESGKPIModel)
        .filter(
            ESGKPIModel.organization_id == organization_id,
            ESGKPIModel.is_active == True,  # noqa: E712
            ESGKPIModel.target_value.isnot(None),
        )
        .all()
    )

    scores_by_category: dict[str, list[float]] = {
        "ENVIRONMENTAL": [],
        "SOCIAL": [],
        "GOVERNANCE": [],
    }
    kpi_breakdown: list[dict] = []

    for kpi in kpis:
        latest = (
            session.query(KPIMeasurementModel)
            .filter(
                KPIMeasurementModel.kpi_id == kpi.id,
                KPIMeasurementModel.period_start >= period_start,
                KPIMeasurementModel.period_end <= period_end,
            )
            .order_by(KPIMeasurementModel.period_end.desc())
            .first()
        )
        if latest is None:
            continue
        attainment = _kpi_attainment(latest.measured_value, kpi.target_value)
        cat = kpi.category
        if cat in scores_by_category:
            scores_by_category[cat].append(attainment)
        kpi_breakdown.append(
            {
                "kpi_id": kpi.id,
                "kpi_name": kpi.name,
                "category": cat,
                "measured": latest.measured_value,
                "target": kpi.target_value,
                "attainment_pct": attainment,
            }
        )

    env_score = (
        round(mean(scores_by_category["ENVIRONMENTAL"]), 2)
        if scores_by_category["ENVIRONMENTAL"]
        else 0.0
    )
    soc_score = (
        round(mean(scores_by_category["SOCIAL"]), 2) if scores_by_category["SOCIAL"] else 0.0
    )
    gov_score = (
        round(mean(scores_by_category["GOVERNANCE"]), 2)
        if scores_by_category["GOVERNANCE"]
        else 0.0
    )
    overall = round(env_score * _ENV_WEIGHT + soc_score * _SOC_WEIGHT + gov_score * _GOV_WEIGHT, 2)

    now = _now()
    sc = SustainabilityScorecardModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        period_start=period_start,
        period_end=period_end,
        environmental_score=env_score,
        social_score=soc_score,
        governance_score=gov_score,
        overall_score=overall,
        calculation_method=(
            f"ENV={_ENV_WEIGHT * 100:.0f}% × avg(ENVIRONMENTAL KPI attainment), "
            f"SOC={_SOC_WEIGHT * 100:.0f}% × avg(SOCIAL KPI attainment), "
            f"GOV={_GOV_WEIGHT * 100:.0f}% × avg(GOVERNANCE KPI attainment)"
        ),
        score_data={
            "weights": {
                "environmental": _ENV_WEIGHT,
                "social": _SOC_WEIGHT,
                "governance": _GOV_WEIGHT,
            },
            "category_scores": {
                "environmental": env_score,
                "social": soc_score,
                "governance": gov_score,
            },
            "kpi_breakdown": kpi_breakdown,
        },
        generated_by=actor_id,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(sc)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.scorecard.computed",
        actor_id=actor_id,
        resource_type="sustainability_scorecard",
        resource_id=sc.id,
        details={"overall_score": overall, "env": env_score, "soc": soc_score, "gov": gov_score},
    )
    return sc


def list_scorecards(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[SustainabilityScorecardModel]:
    return (
        session.query(SustainabilityScorecardModel)
        .filter(SustainabilityScorecardModel.organization_id == organization_id)
        .order_by(SustainabilityScorecardModel.period_end.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── Deterministic Forecasting ─────────────────────────────────────────────────


def _linear_trend(data: list[float]) -> tuple[float, float]:
    """Returns (slope, intercept) for simple linear regression over index positions."""
    n = len(data)
    if n < 2:
        return 0.0, data[0] if data else 0.0
    xs = list(range(n))
    mean_x = mean(xs)
    mean_y = mean(data)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, data, strict=False))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den != 0 else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _moving_average(data: list[float], window: int = 3) -> float:
    """Simple moving average over last `window` points."""
    if not data:
        return 0.0
    tail = data[-window:] if len(data) >= window else data
    return mean(tail)


def create_forecast(
    organization_id: str,
    forecast_type: str,
    method: str,
    period_start: datetime,
    period_end: datetime,
    historical_data: list[float],
    forecast_horizon_months: int,
    actor_id: str,
    session: Session,
    *,
    kpi_id: str | None = None,
    assumptions: dict | None = None,
) -> PerformanceForecastModel:
    if forecast_type not in FORECAST_TYPES:
        raise SustainabilityError(f"Invalid forecast_type: {forecast_type}")
    if method not in FORECAST_METHODS:
        raise SustainabilityError(f"Invalid forecast method: {method}")
    if not historical_data:
        raise SustainabilityError("historical_data must not be empty")

    # Compute deterministic forecast
    if method == "LINEAR_TREND":
        slope, intercept = _linear_trend(historical_data)
        n = len(historical_data)
        forecast_data = [
            round(intercept + slope * (n + i), 6) for i in range(forecast_horizon_months)
        ]
    else:  # MOVING_AVERAGE
        window = min(3, len(historical_data))
        last_avg = _moving_average(historical_data, window)
        forecast_data = [round(last_avg, 6)] * forecast_horizon_months

    now = _now()
    fc = PerformanceForecastModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        kpi_id=kpi_id,
        forecast_type=forecast_type,
        method=method,
        period_start=period_start,
        period_end=period_end,
        forecast_horizon_months=forecast_horizon_months,
        historical_data=historical_data,
        forecast_data=forecast_data,
        confidence_interval=None,
        assumptions=assumptions or {"method": method},
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(fc)
    session.flush()
    return fc


def list_forecasts(
    organization_id: str,
    session: Session,
    *,
    forecast_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[PerformanceForecastModel]:
    q = session.query(PerformanceForecastModel).filter(
        PerformanceForecastModel.organization_id == organization_id
    )
    if forecast_type:
        q = q.filter(PerformanceForecastModel.forecast_type == forecast_type)
    return q.order_by(PerformanceForecastModel.created_at.desc()).limit(limit).offset(offset).all()


# ── Scenario Analysis ─────────────────────────────────────────────────────────


def create_scenario(
    organization_id: str,
    name: str,
    scenario_type: str,
    inputs: dict,
    assumptions: dict,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
) -> ScenarioAnalysisModel:
    if scenario_type not in SCENARIO_TYPES:
        raise SustainabilityError(f"Invalid scenario_type: {scenario_type}")
    # Deterministic output calculation based on scenario type
    outputs = _compute_scenario_outputs(scenario_type, inputs, assumptions)
    now = _now()
    sc = ScenarioAnalysisModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        scenario_type=scenario_type,
        description=description,
        inputs=inputs,
        assumptions=assumptions,
        outputs=outputs,
        scenario_status="COMPLETE",
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(sc)
    session.flush()
    return sc


def _compute_scenario_outputs(scenario_type: str, inputs: dict, assumptions: dict) -> dict:
    """Deterministic scenario calculations. All formulas are explicit and auditable."""
    if scenario_type == "SUPPLIER_IMPROVEMENT":
        baseline = float(inputs.get("baseline_supplier_compliance", 0))
        improvement = float(assumptions.get("improvement_percent", 10))
        projected = min(100.0, round(baseline * (1 + improvement / 100), 2))
        return {
            "projected_supplier_compliance": projected,
            "improvement_pct": improvement,
            "formula": "projected = baseline × (1 + improvement_pct / 100)",
        }
    elif scenario_type == "RENEWABLE_TRANSITION":
        baseline_emissions = float(inputs.get("baseline_scope2_emissions", 0))
        renewable_pct = float(assumptions.get("renewable_percent", 50))
        reduction = round(baseline_emissions * renewable_pct / 100, 6)
        projected = round(baseline_emissions - reduction, 6)
        return {
            "projected_scope2_emissions": projected,
            "emissions_reduction": reduction,
            "renewable_percent": renewable_pct,
            "formula": "reduction = baseline_scope2 × renewable_pct / 100",
        }
    elif scenario_type == "EMISSIONS_INTENSITY_REDUCTION":
        baseline_intensity = float(inputs.get("baseline_intensity", 0))
        revenue = float(inputs.get("revenue", 1))
        intensity_reduction_pct = float(assumptions.get("intensity_reduction_percent", 10))
        new_intensity = round(baseline_intensity * (1 - intensity_reduction_pct / 100), 6)
        projected_total = round(new_intensity * revenue, 6)
        return {
            "new_intensity": new_intensity,
            "projected_total_emissions": projected_total,
            "formula": "new_intensity = baseline_intensity × (1 - reduction_pct / 100); total = new_intensity × revenue",
        }
    else:  # CUSTOM
        return {"note": "Custom scenario — outputs must be provided manually", "inputs": inputs}


def list_scenarios(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[ScenarioAnalysisModel]:
    return (
        session.query(ScenarioAnalysisModel)
        .filter(ScenarioAnalysisModel.organization_id == organization_id)
        .order_by(ScenarioAnalysisModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
