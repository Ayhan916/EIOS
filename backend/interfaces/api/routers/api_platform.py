"""
M30 API Platform Router

Endpoints for API key management, service accounts, webhooks, and delivery logs.
All management endpoints require ADMIN role (JWT only — API keys cannot manage themselves).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

import application.audit as audit_factory
from application.api_platform.key_service import generate_api_key
from application.api_platform.webhook_service import (
    attempt_delivery,
    payload_hash,
)
from domain.api_key import ApiKey
from domain.enums import EntityStatus
from domain.service_account import ServiceAccount
from domain.webhook_delivery import WebhookDelivery
from domain.webhook_subscription import WebhookSubscription
from infrastructure.persistence.repositories import (
    SQLApiKeyRepository,
    SQLAuditEventRepository,
    SQLServiceAccountRepository,
    SQLWebhookDeliveryRepository,
    SQLWebhookSubscriptionRepository,
)
from interfaces.api.deps import (
    get_api_key_repo,
    get_audit_event_repo,
    get_current_user,
    get_service_account_repo,
    get_webhook_delivery_repo,
    get_webhook_subscription_repo,
    require_admin,
)
from interfaces.api.schemas.api_platform import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ApiKeyUsageSummary,
    ServiceAccountCreate,
    ServiceAccountResponse,
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
)
from domain.user import User

log = structlog.get_logger()

router = APIRouter(prefix="/platform", tags=["API Platform"])


def _org(user: User) -> str:
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    return user.organization_id


# ── Service Accounts ──────────────────────────────────────────────────────────


@router.post("/service-accounts", response_model=ServiceAccountResponse, status_code=201)
async def create_service_account(
    body: ServiceAccountCreate,
    current_user: User = Depends(require_admin),
    repo: SQLServiceAccountRepository = Depends(get_service_account_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> ServiceAccountResponse:
    org_id = _org(current_user)
    sa = ServiceAccount(
        organization_id=org_id,
        name=body.name,
        description=body.description,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    saved = await repo.save(sa)
    await audit_repo.save(
        audit_factory.make(
            action="service_account.created",
            actor_id=current_user.id,
            actor_email=current_user.email,
            entity_type="ServiceAccount",
            entity_id=saved.id,
            detail=f"Service account created: {body.name}",
            metadata={"organization_id": org_id},
        )
    )
    return ServiceAccountResponse(
        id=saved.id,
        organization_id=saved.organization_id,
        name=saved.name,
        description=saved.description,
        is_active=saved.is_active,
        created_at=saved.created_at,
        created_by=saved.created_by,
    )


@router.get("/service-accounts", response_model=list[ServiceAccountResponse])
async def list_service_accounts(
    current_user: User = Depends(require_admin),
    repo: SQLServiceAccountRepository = Depends(get_service_account_repo),
) -> list[ServiceAccountResponse]:
    org_id = _org(current_user)
    accounts = await repo.list_for_org(org_id)
    return [
        ServiceAccountResponse(
            id=sa.id,
            organization_id=sa.organization_id,
            name=sa.name,
            description=sa.description,
            is_active=sa.is_active,
            created_at=sa.created_at,
            created_by=sa.created_by,
        )
        for sa in accounts
    ]


@router.post("/service-accounts/{sa_id}/deactivate", status_code=200)
async def deactivate_service_account(
    sa_id: str,
    current_user: User = Depends(require_admin),
    repo: SQLServiceAccountRepository = Depends(get_service_account_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> dict:
    org_id = _org(current_user)
    sa = await repo.get_by_id(sa_id)
    if sa is None or sa.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Service account not found")
    sa.is_active = False
    await repo.save(sa)
    await audit_repo.save(
        audit_factory.make(
            action="service_account.deactivated",
            actor_id=current_user.id,
            actor_email=current_user.email,
            entity_type="ServiceAccount",
            entity_id=sa_id,
            detail=f"Service account deactivated: {sa.name}",
            metadata={"organization_id": org_id},
        )
    )
    return {"detail": "Service account deactivated"}


# ── API Keys ──────────────────────────────────────────────────────────────────


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: ApiKeyCreate,
    current_user: User = Depends(require_admin),
    repo: SQLApiKeyRepository = Depends(get_api_key_repo),
    sa_repo: SQLServiceAccountRepository = Depends(get_service_account_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> ApiKeyCreatedResponse:
    org_id = _org(current_user)

    # Validate service account belongs to org if specified
    if body.service_account_id:
        sa = await sa_repo.get_by_id(body.service_account_id)
        if sa is None or sa.organization_id != org_id or not sa.is_active:
            raise HTTPException(status_code=400, detail="Service account not found or inactive")

    raw_key, key_hash, key_prefix = generate_api_key()

    api_key = ApiKey(
        organization_id=org_id,
        service_account_id=body.service_account_id,
        name=body.name,
        description=body.description,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=body.scopes,
        is_active=True,
        rate_limit_per_minute=body.rate_limit_per_minute,
        rate_limit_per_hour=body.rate_limit_per_hour,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    saved = await repo.save(api_key)
    await audit_repo.save(
        audit_factory.make(
            action="api_key.created",
            actor_id=current_user.id,
            actor_email=current_user.email,
            entity_type="ApiKey",
            entity_id=saved.id,
            detail=f"API key created: {body.name} ({key_prefix}***)",
            metadata={"organization_id": org_id, "scopes": body.scopes},
        )
    )
    return ApiKeyCreatedResponse(
        id=saved.id,
        name=saved.name,
        key_prefix=key_prefix,
        raw_key=raw_key,
        scopes=saved.scopes,
        rate_limit_per_minute=saved.rate_limit_per_minute,
        rate_limit_per_hour=saved.rate_limit_per_hour,
        created_at=saved.created_at,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(require_admin),
    repo: SQLApiKeyRepository = Depends(get_api_key_repo),
) -> list[ApiKeyResponse]:
    org_id = _org(current_user)
    keys = await repo.list_for_org(org_id)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            description=k.description,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            is_active=k.is_active,
            service_account_id=k.service_account_id,
            last_used_at=k.last_used_at,
            requests_total=k.requests_total,
            rate_limit_per_minute=k.rate_limit_per_minute,
            rate_limit_per_hour=k.rate_limit_per_hour,
            revoked_at=k.revoked_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post("/api-keys/{key_id}/revoke", status_code=200)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(require_admin),
    repo: SQLApiKeyRepository = Depends(get_api_key_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> dict:
    org_id = _org(current_user)
    api_key = await repo.get_by_id(key_id)
    if api_key is None or api_key.organization_id != org_id:
        raise HTTPException(status_code=404, detail="API key not found")
    if not api_key.is_active:
        raise HTTPException(status_code=400, detail="API key is already revoked")
    api_key.is_active = False
    api_key.revoked_at = datetime.now(UTC)
    api_key.revoked_by = current_user.id
    await repo.save(api_key)
    await audit_repo.save(
        audit_factory.make(
            action="api_key.revoked",
            actor_id=current_user.id,
            actor_email=current_user.email,
            entity_type="ApiKey",
            entity_id=key_id,
            detail=f"API key revoked: {api_key.name} ({api_key.key_prefix}***)",
            metadata={"organization_id": org_id},
        )
    )
    return {"detail": "API key revoked"}


@router.get("/api-keys/usage", response_model=list[ApiKeyUsageSummary])
async def api_key_usage_summary(
    current_user: User = Depends(require_admin),
    repo: SQLApiKeyRepository = Depends(get_api_key_repo),
) -> list[ApiKeyUsageSummary]:
    org_id = _org(current_user)
    keys = await repo.list_for_org(org_id)
    return [
        ApiKeyUsageSummary(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            requests_total=k.requests_total,
            last_used_at=k.last_used_at,
            is_active=k.is_active,
        )
        for k in keys
    ]


# ── Webhooks ──────────────────────────────────────────────────────────────────


@router.post("/webhooks", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    current_user: User = Depends(require_admin),
    repo: SQLWebhookSubscriptionRepository = Depends(get_webhook_subscription_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> WebhookResponse:
    org_id = _org(current_user)
    sub = WebhookSubscription(
        organization_id=org_id,
        name=body.name,
        target_url=body.target_url,
        secret=body.secret,
        events=body.events,
        is_active=True,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    saved = await repo.save(sub)
    await audit_repo.save(
        audit_factory.make(
            action="webhook.created",
            actor_id=current_user.id,
            actor_email=current_user.email,
            entity_type="WebhookSubscription",
            entity_id=saved.id,
            detail=f"Webhook created: {body.name} → {body.target_url}",
            metadata={"organization_id": org_id, "events": body.events},
        )
    )
    return _webhook_response(saved)


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(require_admin),
    repo: SQLWebhookSubscriptionRepository = Depends(get_webhook_subscription_repo),
) -> list[WebhookResponse]:
    org_id = _org(current_user)
    subs = await repo.list_for_org(org_id)
    return [_webhook_response(s) for s in subs]


@router.patch("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    body: WebhookUpdate,
    current_user: User = Depends(require_admin),
    repo: SQLWebhookSubscriptionRepository = Depends(get_webhook_subscription_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> WebhookResponse:
    org_id = _org(current_user)
    sub = await repo.get_by_id(webhook_id)
    if sub is None or sub.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if body.name is not None:
        sub.name = body.name
    if body.target_url is not None:
        sub.target_url = body.target_url
    if body.events is not None:
        sub.events = body.events
    if body.is_active is not None:
        sub.is_active = body.is_active
    saved = await repo.save(sub)
    if body.is_active is False:
        await audit_repo.save(
            audit_factory.make(
                action="webhook.disabled",
                actor_id=current_user.id,
                actor_email=current_user.email,
                entity_type="WebhookSubscription",
                entity_id=webhook_id,
                detail=f"Webhook disabled: {saved.name}",
                metadata={"organization_id": org_id},
            )
        )
    return _webhook_response(saved)


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(require_admin),
    repo: SQLWebhookSubscriptionRepository = Depends(get_webhook_subscription_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> None:
    org_id = _org(current_user)
    sub = await repo.get_by_id(webhook_id)
    if sub is None or sub.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    sub.is_active = False
    sub.status = EntityStatus.DELETED
    await repo.save(sub)
    await audit_repo.save(
        audit_factory.make(
            action="webhook.deleted",
            actor_id=current_user.id,
            actor_email=current_user.email,
            entity_type="WebhookSubscription",
            entity_id=webhook_id,
            detail=f"Webhook deleted: {sub.name}",
            metadata={"organization_id": org_id},
        )
    )


# ── Delivery Logs ─────────────────────────────────────────────────────────────


@router.get("/webhooks/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_admin),
    sub_repo: SQLWebhookSubscriptionRepository = Depends(get_webhook_subscription_repo),
    delivery_repo: SQLWebhookDeliveryRepository = Depends(get_webhook_delivery_repo),
) -> list[WebhookDeliveryResponse]:
    org_id = _org(current_user)
    sub = await sub_repo.get_by_id(webhook_id)
    if sub is None or sub.organization_id != org_id or sub.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Webhook not found")
    deliveries = await delivery_repo.list_for_subscription(webhook_id, limit=limit)
    return [_delivery_response(d) for d in deliveries]


@router.get("/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_all_deliveries(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_admin),
    delivery_repo: SQLWebhookDeliveryRepository = Depends(get_webhook_delivery_repo),
) -> list[WebhookDeliveryResponse]:
    org_id = _org(current_user)
    deliveries = await delivery_repo.list_for_org(org_id, limit=limit)
    return [_delivery_response(d) for d in deliveries]


@router.get("/deliveries/stats")
async def delivery_stats(
    current_user: User = Depends(require_admin),
    delivery_repo: SQLWebhookDeliveryRepository = Depends(get_webhook_delivery_repo),
) -> dict:
    """Return webhook delivery counts grouped by status for the caller's organization."""
    org_id = _org(current_user)
    return await delivery_repo.count_by_status_for_org(org_id)


# ── Webhook dispatch (internal) ───────────────────────────────────────────────


async def dispatch_webhook_event(
    organization_id: str,
    event_type: str,
    payload: dict,
) -> None:
    """Fire webhook deliveries for an event.

    Self-contained: opens its own DB session so it can be called as a
    FastAPI BackgroundTask without depending on the request-scoped session.
    Delivery records are committed before asyncio tasks are spawned so that
    _attempt_delivery can find them via their own session.
    """
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415

    full_payload = {
        "event": event_type,
        "organization_id": organization_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": payload,
    }
    p_hash = payload_hash(full_payload)

    delivery_targets: list[tuple[str, str, str]] = []  # (target_url, secret, delivery_id)
    async with AsyncSessionFactory() as session, session.begin():
        sub_repo = SQLWebhookSubscriptionRepository(session)
        delivery_repo = SQLWebhookDeliveryRepository(session)

        subs = await sub_repo.list_active_for_event(organization_id, event_type)
        if not subs:
            return

        for sub in subs:
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event_type=event_type,
                payload_hash=p_hash,
                payload=full_payload,
                delivery_status="pending",
                retry_count=0,
                status=EntityStatus.ACTIVE,
            )
            saved = await delivery_repo.save(delivery)
            delivery_targets.append((sub.target_url, sub.secret, saved.id))

    # Deliveries committed — now fire asyncio tasks safely
    for target_url, secret, delivery_id in delivery_targets:
        asyncio.create_task(
            attempt_delivery(target_url, secret, full_payload, event_type, delivery_id)
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _webhook_response(sub: WebhookSubscription) -> WebhookResponse:
    return WebhookResponse(
        id=sub.id,
        name=sub.name,
        target_url=sub.target_url,
        events=sub.events,
        is_active=sub.is_active,
        failure_count=sub.failure_count,
        last_triggered_at=sub.last_triggered_at,
        created_at=sub.created_at,
    )


def _delivery_response(d: WebhookDelivery) -> WebhookDeliveryResponse:
    return WebhookDeliveryResponse(
        id=d.id,
        subscription_id=d.subscription_id,
        event_type=d.event_type,
        delivery_status=d.delivery_status,
        response_code=d.response_code,
        duration_ms=d.duration_ms,
        retry_count=d.retry_count,
        error_message=d.error_message,
        delivered_at=d.delivered_at,
        created_at=d.created_at,
    )
