"""M44 — Deterministic Forecast Engine service.

Three methodology implementations — all explainable, reproducible, auditable.
No ML. No LLM.

LINEAR_TREND:
  forecast = baseline + slope * years_ahead
  Parameters: {"slope": float}

WEIGHTED_MOVING_AVERAGE:
  forecast = sum(w_i * v_i) / sum(w_i)  over the last N historical values
  Parameters: {"weights": [float, ...], "historical_values": [float, ...]}

SCENARIO_PROJECTION:
  forecast = baseline * (1 + annual_change_pct/100) ^ years_ahead
  Parameters: {"annual_change_pct": float, "baseline_year": int}
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.metrics import strategy_counters
from application.strategy.digital_twin_service import StrategyError
from infrastructure.persistence.models.strategy import (
    FORECAST_METHODOLOGIES,
    FORECAST_TYPES,
    ForecastMethodologyRecordModel,
    ForecastModelRecord,
    ForecastResultModel,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise StrategyError(f"{label} not found")


# ── Deterministic forecast algorithms ────────────────────────────────────────

def _linear_trend(baseline_value: float, slope: float, years_ahead: int) -> float:
    """f(t) = baseline + slope * t"""
    return round(baseline_value + slope * years_ahead, 6)


def _weighted_moving_average(historical_values: list[float], weights: list[float]) -> float:
    """WMA = sum(w_i * v_i) / sum(w_i) over last min(len(weights), len(values)) points."""
    if not historical_values or not weights:
        raise StrategyError("historical_values and weights required for WMA")
    n = min(len(historical_values), len(weights))
    vals = historical_values[-n:]
    wts = weights[:n]
    total_w = sum(wts)
    if total_w == 0:
        raise StrategyError("weights must sum to non-zero")
    return round(sum(w * v for w, v in zip(wts, vals)) / total_w, 6)


def _scenario_projection(baseline_value: float, annual_change_pct: float, years_ahead: int) -> float:
    """Compound: baseline * (1 + rate)^n"""
    return round(baseline_value * ((1 + annual_change_pct / 100) ** years_ahead), 6)


def _run_forecast_algorithm(
    methodology: str,
    baseline_value: float,
    forecast_year: int,
    parameters: dict,
) -> tuple[float, float, float, float]:
    """Returns (forecast_value, lower_bound, upper_bound, confidence_level)."""
    import datetime as _dt
    current_year = _dt.datetime.now(_dt.timezone.utc).year
    years_ahead = max(1, forecast_year - current_year)

    if methodology == "LINEAR_TREND":
        slope = parameters.get("slope", 0.0)
        fv = _linear_trend(baseline_value, slope, years_ahead)
        uncertainty = abs(slope * years_ahead * 0.10)
        conf = max(0.5, min(0.99, 1.0 - 0.05 * years_ahead))

    elif methodology == "WEIGHTED_MOVING_AVERAGE":
        historical = parameters.get("historical_values", [baseline_value])
        weights = parameters.get("weights", [1.0])
        fv = _weighted_moving_average(historical, weights)
        uncertainty = abs(fv * 0.08)
        conf = 0.80

    elif methodology == "SCENARIO_PROJECTION":
        annual_change_pct = parameters.get("annual_change_pct", 0.0)
        fv = _scenario_projection(baseline_value, annual_change_pct, years_ahead)
        uncertainty = abs(fv - baseline_value) * 0.15
        conf = max(0.5, min(0.95, 1.0 - 0.03 * years_ahead))

    else:
        raise StrategyError(f"Unknown methodology: {methodology}")

    lower = round(fv - uncertainty, 6)
    upper = round(fv + uncertainty, 6)
    return round(fv, 6), lower, upper, round(conf, 4)


# ── Forecast Methodology Record (AI Governance integration) ───────────────────

def create_forecast_methodology(
    organization_id: str,
    methodology_name: str,
    algorithm_type: str,
    actor_id: str,
    session: Session,
    *,
    methodology_version: str = "1.0.0",
    description: str | None = None,
    parameters_schema: dict | None = None,
    explainability_notes: str | None = None,
) -> ForecastMethodologyRecordModel:
    if algorithm_type not in FORECAST_METHODOLOGIES:
        raise StrategyError(f"Invalid algorithm_type: {algorithm_type}")
    now = _now()
    record = ForecastMethodologyRecordModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        methodology_name=methodology_name,
        methodology_version=methodology_version,
        description=description,
        algorithm_type=algorithm_type,
        parameters_schema=parameters_schema,
        explainability_notes=explainability_notes,
        is_approved=False,
        approved_by=None,
        review_date=None,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record


# ── Forecast Model ────────────────────────────────────────────────────────────

def create_forecast_model(
    organization_id: str,
    model_name: str,
    methodology: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    parameters: dict | None = None,
    model_version: str = "1.0.0",
    methodology_record_id: str | None = None,
) -> ForecastModelRecord:
    if methodology not in FORECAST_METHODOLOGIES:
        raise StrategyError(f"Invalid methodology: {methodology}")
    now = _now()
    model = ForecastModelRecord(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        model_name=model_name,
        methodology=methodology,
        description=description,
        parameters=parameters or {},
        model_version=model_version,
        is_approved=False,
        approved_by=None,
        methodology_record_id=methodology_record_id,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.forecast_model.created",
        actor_id=actor_id,
        resource_type="forecast_model",
        resource_id=model.id,
        details={"model_name": model_name, "methodology": methodology},
    )
    strategy_counters.record_forecast_model()
    return model


# ── Forecast Run ──────────────────────────────────────────────────────────────

def run_forecast(
    organization_id: str,
    forecast_model_id: str,
    forecast_type: str,
    target_metric: str,
    forecast_year: int,
    baseline_value: float,
    actor_id: str,
    session: Session,
    *,
    scenario_id: str | None = None,
    parameter_overrides: dict | None = None,
) -> ForecastResultModel:
    if forecast_type not in FORECAST_TYPES:
        raise StrategyError(f"Invalid forecast_type: {forecast_type}")
    model = session.get(ForecastModelRecord, forecast_model_id)
    _assert_org(model, organization_id, "forecast model")

    params = {**(model.parameters or {}), **(parameter_overrides or {})}
    if model.methodology == "WEIGHTED_MOVING_AVERAGE":
        window = len(params.get("weights", [1.0]))
        validate_wma_window(organization_id, window, session)
    fv, lower, upper, conf = _run_forecast_algorithm(
        model.methodology, baseline_value, forecast_year, params
    )

    now = _now()
    result = ForecastResultModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        forecast_model_id=forecast_model_id,
        forecast_type=forecast_type,
        target_metric=target_metric,
        forecast_year=forecast_year,
        baseline_value=baseline_value,
        forecast_value=fv,
        lower_bound=lower,
        upper_bound=upper,
        confidence_level=conf,
        scenario_id=scenario_id,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(result)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.forecast.generated",
        actor_id=actor_id,
        resource_type="forecast_result",
        resource_id=result.id,
        details={
            "forecast_model_id": forecast_model_id,
            "forecast_type": forecast_type,
            "target_metric": target_metric,
            "forecast_year": forecast_year,
            "methodology": model.methodology,
        },
    )
    strategy_counters.record_forecast()
    return result


def validate_wma_window(
    organization_id: str,
    window_size: int,
    session: Session,
) -> None:
    """Enforce the active ForecastWindowPolicy for this org, if one exists.

    No policy → window is unrestricted.
    """
    from infrastructure.persistence.models.strategy import ForecastWindowPolicyModel

    policy = (
        session.query(ForecastWindowPolicyModel)
        .filter(
            ForecastWindowPolicyModel.organization_id == organization_id,
            ForecastWindowPolicyModel.is_active.is_(True),
        )
        .order_by(ForecastWindowPolicyModel.created_at.desc())
        .first()
    )
    if policy is None:
        return
    if window_size < policy.min_window:
        raise StrategyError(
            f"WMA window {window_size} is below minimum {policy.min_window} "
            f"set by policy '{policy.policy_name}'"
        )
    if window_size > policy.max_window:
        raise StrategyError(
            f"WMA window {window_size} exceeds maximum {policy.max_window} "
            f"set by policy '{policy.policy_name}'"
        )


def create_forecast_window_policy(
    organization_id: str,
    policy_name: str,
    min_window: int,
    max_window: int,
    default_window: int,
    actor_id: str,
    session: Session,
    *,
    applicable_methodology: str = "WEIGHTED_MOVING_AVERAGE",
):
    from infrastructure.persistence.models.strategy import ForecastWindowPolicyModel
    import uuid as _uuid

    if min_window < 1:
        raise StrategyError("min_window must be >= 1")
    if max_window < min_window:
        raise StrategyError("max_window must be >= min_window")
    if not (min_window <= default_window <= max_window):
        raise StrategyError("default_window must be within [min_window, max_window]")
    now = _now()
    policy = ForecastWindowPolicyModel(
        id=str(_uuid.uuid4()),
        organization_id=organization_id,
        policy_name=policy_name,
        min_window=min_window,
        max_window=max_window,
        default_window=default_window,
        applicable_methodology=applicable_methodology,
        is_active=True,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(policy)
    session.flush()
    return policy


def list_forecast_window_policies(organization_id: str, session: Session):
    from infrastructure.persistence.models.strategy import ForecastWindowPolicyModel

    return (
        session.query(ForecastWindowPolicyModel)
        .filter(ForecastWindowPolicyModel.organization_id == organization_id)
        .order_by(ForecastWindowPolicyModel.created_at.desc())
        .all()
    )


def list_forecast_models(organization_id: str, session: Session) -> list[ForecastModelRecord]:
    return (
        session.query(ForecastModelRecord)
        .filter(ForecastModelRecord.organization_id == organization_id)
        .order_by(ForecastModelRecord.created_at.desc())
        .all()
    )


def list_forecast_results(organization_id: str, session: Session) -> list[ForecastResultModel]:
    return (
        session.query(ForecastResultModel)
        .filter(ForecastResultModel.organization_id == organization_id)
        .order_by(ForecastResultModel.created_at.desc())
        .all()
    )
