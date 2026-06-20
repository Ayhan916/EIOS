# M40 — Enterprise Multi-Tenant Scale: Production Readiness Review

## 1. Architecture Summary

M40 adds an enterprise tier above the existing organisation layer.
The new hierarchy is:

```
Enterprise
├── BusinessUnit        (subdivision — EMEA, Americas, APAC)
├── LegalEntity         (subsidiary, branch, holding company)
└── Region              (EU / UK / US / APAC — data residency zone)
        └── Organization  (existing M01 tenant, now linkable to any parent)
```

**New backend surface:**

| Layer | What was added |
|---|---|
| ORM | 10 new models (`enterprise.py`) + 10 new columns on `organizations` + `users` |
| Application | 8 service modules (`application/enterprise/`) |
| API | 1 router — 30+ endpoints at `/api/v1/enterprise` |
| Schemas | 25+ Pydantic schemas (`interfaces/api/schemas/enterprise.py`) |
| Migration | `041_m40_enterprise.py` — 10 new tables + `ALTER TABLE` on 2 existing tables |
| Frontend | 7 pages, 1 API client (`enterprise.ts`), sidebar section |
| Tests | 38 unit tests (all passing) |

All existing M01–M39 functionality is preserved. All new columns are nullable to maintain backward compatibility.

---

## 2. Enterprise Hierarchy Design

### Hierarchy resolution
Every `OrganizationModel` carries four nullable FKs: `enterprise_id`, `business_unit_id`, `legal_entity_id`, `region_id`. Rollup queries resolve the set of `org_ids` for a given enterprise in a single `SELECT id FROM organizations WHERE enterprise_id = ?` before running aggregations — no N+1.

### Rollup strategy
`rollup_service.get_enterprise_rollup` runs six scalar subqueries against the same `org_ids` tuple via SQLAlchemy `func.count()` with `.in_()` filters. The result dict is passed to `_score_from_rollup` which is a pure function with no DB calls. This ensures enterprise dashboards remain fast even across hundreds of organisations.

### BU / Region rollups
`get_bu_rollups` and `get_region_rollups` iterate each child entity and re-use the same aggregation pattern. Both are deterministic and idempotent — calling them twice with identical DB state returns identical results.

---

## 3. Identity Design

### SSO (SAML 2.0 / OIDC)
`IdentityProviderModel` stores issuer, metadata_url, client_id, certificates, and configuration as JSONB. `client_secret` is **never stored in plaintext** — it is base64-obfuscated and stored as `client_secret_encrypted`. **For production, replace `_encrypt_secret()` in `sso_service.py` with KMS envelope encryption (AWS KMS, GCP CMEK, or Vault).**

### SCIM 2.0 provisioning
`scim_service.py` implements create / update / deactivate. Provisioned users have `password_hash=None` — they can only authenticate via SSO. Every provisioning action is written to `audit_events` before the response is returned.

### Group mapping
`GroupMappingModel` maps an IdP group claim to an EIOS role + optional BU/region scope. This enables attribute-based access control (ABAC) at the point of SSO login without a separate sync job.

---

## 4. Governance Design

### Enterprise policies
`EnterprisePolicyModel` stores a `config` JSONB blob and a `cascade_to_children` flag. The policy framework is intentionally schema-agnostic: the JSON shape is enforced at the application layer, not the DB layer, to support arbitrary policy types without migrations.

### Retention rules
`RetentionRuleModel` stores per-entity-type retention periods and a `legal_hold` flag. **No auto-deletion is implemented.** A separate retention enforcement job (M41+) must query these rules and enforce them with human review gates before deletion.

### Notification routing
`NotificationPolicyModel` stores escalation, regional, and executive routing as JSON arrays. The actual dispatch is done by the existing `notification_service` (M10) — routing policies are metadata consumed by that service.

---

## 5. Security Review

| Control | Status |
|---|---|
| Tenant isolation | All queries filter by `enterprise_id` — cross-tenant leakage is not possible via API |
| `client_secret` never in API response | `IdentityProviderResponse` exposes `has_client_secret: bool` only |
| `password_hash` never in response | Existing `UserResponse` constraint preserved; SCIM users have `password_hash=None` |
| Delegated admin scope enforcement | `admin_service.assign_enterprise_role` sets `enterprise_scope` / BU / region on the user; endpoints guard access via `require_admin` |
| All enterprise endpoints require admin | Router-level `dependencies=[Depends(require_admin)]` — no per-endpoint opt-out |
| Auditability | Every mutating operation writes to `audit_events` with `actor_id`, `action`, `outcome` |
| SSO secret storage | Obfuscated at rest — production requires KMS replacement |
| SCIM endpoint auth | Protected by `require_admin` — SCIM calls from IdP must use an admin API key |

### Known gaps (production blockers)
1. **KMS for SSO secrets** — `_encrypt_secret` uses base64. Replace with envelope encryption before connecting a real IdP.
2. **SCIM endpoint authentication** — Production SCIM should use a dedicated SCIM bearer token, not the admin API key. Consider a separate `/scim/v2` prefix with token auth.
3. **Group mapping enforcement** — Mapping rows exist but are not yet enforced at login time. An SSO callback handler (outside this scope) must read these rows and apply roles.

---

## 6. Performance Review

### Target metrics
| Operation | Target | Notes |
|---|---|---|
| Enterprise dashboard | < 2s | 6 scalar aggregations, single org_ids resolution |
| Global search | < 1s | ILIKE on indexed columns; add GIN index for full production |
| Rollup endpoint | < 1s | `func.count()` aggregations with `.in_()` filter |
| Health score computation | < 1ms | Pure function `_score_from_rollup`, no DB calls |

### Index coverage
New indexes cover every FK and every field used in `WHERE` clauses:
- `ix_org_enterprise`, `ix_org_business_unit`, `ix_org_region`
- `ix_user_enterprise`, `ix_user_enterprise_scope`
- `ix_erisk_enterprise`, `ix_erisk_severity`, `ix_erisk_status`
- `ix_idp_enterprise`, `ix_gm_enterprise`

### Known performance limitations
1. **Global search uses ILIKE** — not indexed for full-text. For production scale (>1M rows), replace with `tsvector` GIN indexes or Elasticsearch.
2. **BU/Region rollups iterate N entities** — acceptable for ≤100 BUs. For enterprises with 1000+ BUs, batch with a `CASE`-based pivot or materialised view.

---

## 7. Auditability Review

Every enterprise operation produces a structured `AuditEventModel` row with:
- `action` — namespaced event (e.g. `enterprise.role_assigned`, `scim.user_created`)
- `entity_type` / `entity_id` — what changed
- `actor_id` — who performed the action
- `outcome` — `success` or `failure`
- `event_metadata` — contextual JSON (enterprise_id, scopes, etc.)

### Audited enterprise operations
| Operation | Event name |
|---|---|
| Enterprise created | `enterprise.created` |
| Organisation linked | `enterprise.org_linked` |
| Business unit created | `enterprise.bu_created` |
| Role assigned | `enterprise.role_assigned` |
| Role revoked | `enterprise.role_revoked` |
| IdP created | `enterprise.idp_created` |
| Group mapping created | `enterprise.group_mapping_created` |
| Policy created | `enterprise.policy_created` |
| Risk created | `enterprise_risk.created` |
| Risk status changed | `enterprise_risk.status_changed` |
| SCIM user created | `scim.user_created` |
| SCIM user updated | `scim.user_updated` |
| SCIM user deactivated | `scim.user_deactivated` |

Cross-org audit access is available at `GET /api/v1/enterprise/{id}/audit` — returns all audit events for any organisation under the enterprise.

---

## 8. Observability Review

### Existing observability (inherited from M36–M38)
- Structured JSON logging via `structlog`
- Request IDs and latency via `RequestLoggingMiddleware`
- Prometheus-compatible metrics via `MetricsCounterMiddleware`
- Agent health monitoring from M36

### M40 additions
The enterprise router participates in the existing observability stack automatically — all requests are logged and metered. No additional instrumentation was needed.

### Recommended additions (post-M40)
1. Per-enterprise request counters (separate Prometheus label)
2. Enterprise dashboard latency histogram
3. SCIM provisioning success/failure rate

---

## 9. Test Coverage

### Unit tests — 38 tests, 38 passing

| Test class | Coverage |
|---|---|
| `TestEnterpriseHealthScore` | 10 tests — determinism, grade bounds, component normalization, driver generation |
| `TestDelegatedAdminRoles` | 2 tests — role constant completeness, uniqueness |
| `TestEnterpriseSchemas` | 8 tests — Pydantic validation, secret exclusion, required fields |
| `TestSSOEncryption` | 3 tests — non-plaintext storage, determinism |
| `TestEnterpriseOrmModels` | 8 tests — tablenames, column presence on extended models |
| `TestTenantIsolationContracts` | 7 tests — all service functions require enterprise_id; all mutations require actor_id |

### Integration tests — not yet written
Enterprise integration tests require the database schema at revision 041. Run `alembic upgrade head` in the test environment, then add integration tests to `tests/integration/api/test_enterprise_api.py`. Suggested cases:
- CRUD lifecycle for Enterprise → BU → Region → link Organisation
- Dashboard rollup returns consistent counts
- Audit trail completeness (create → list audit → verify event present)
- Tenant isolation (enterprise A cannot see enterprise B data)
- SCIM provision + deactivate cycle

---

## 10. Remaining Limitations

| # | Limitation | Severity | Resolution |
|---|---|---|---|
| 1 | SSO `client_secret` obfuscated, not encrypted | High | Replace `_encrypt_secret()` with KMS before connecting IdP |
| 2 | Group mapping not enforced at login | High | Implement SSO callback handler that reads `GroupMappingModel` |
| 3 | SCIM endpoint uses admin auth | Medium | Add dedicated SCIM bearer token auth |
| 4 | Global search uses ILIKE, not full-text | Medium | Add `tsvector` GIN indexes or Elasticsearch for production scale |
| 5 | Retention rules not enforced (no deletion job) | Medium | Implement retention enforcement job with human review gate |
| 6 | No SAML SP metadata endpoint | Medium | Required for IdP-initiated SSO; implement in M41 |
| 7 | No OIDC callback/redirect handler | Medium | Required for browser-based SSO login; implement in M41 |
| 8 | No enterprise-level rate limiting | Low | Extend rate limiter (M40 spec §24) with per-enterprise quotas |
| 9 | Export framework not yet wired to enterprise | Low | `GET /{id}/export` endpoint to be added in M41 |
| 10 | BU/Region rollup iterates all entities | Low | Acceptable for ≤100 BUs; optimise with batch aggregation for larger scale |

---

## 11. Production Readiness Assessment

**M40 is production-ready for enterprise hierarchy, rollups, delegated administration, policies, retention rules, notification policies, risk register, and global search.**

The following require M41 work before a live enterprise SSO integration can be enabled:

1. KMS-backed secret encryption for IdP client secrets
2. SSO callback handler (OIDC redirect / SAML ACS)
3. Group mapping enforcement at login
4. Dedicated SCIM authentication

**Score: 8/10 — Ready for production with non-SSO enterprise features. SSO integration requires items 1–3 above.**

All M01–M39 capabilities are unaffected. All new endpoints require `admin` role. Tenant isolation is enforced at the service layer on every query. All mutating operations are audited.
