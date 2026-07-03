from fastapi import APIRouter, Depends, Query

from domain.user import User
from interfaces.api.deps import get_current_user, scope_gate

router = APIRouter(
    prefix="/automations",
    tags=["automations"],
    dependencies=[Depends(get_current_user), Depends(scope_gate("automations:read"))],
)

_activity_log: list[dict] = []


@router.post("/trigger")
async def trigger_automation(
    body: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    entry = {
        "id": f"evt_{len(_activity_log) + 1}",
        "rule_id": body.get("rule_id", ""),
        "entity_type": body.get("entity_type", ""),
        "triggered_at": "",
        "status": "ok",
        "payload": body.get("payload", {}),
        "triggered_by": current_user.id,
    }
    _activity_log.append(entry)
    return {"status": "ok", "event_id": entry["id"]}


@router.get("/activity")
async def get_activity(
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return _activity_log[-limit:]


@router.post("/rules/batch")
async def save_rules_batch(
    body: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"status": "ok", "saved": len(body.get("rules", {}))}
