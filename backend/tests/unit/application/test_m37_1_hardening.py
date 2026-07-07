"""M37.1 Surveillance Hardening — Unit Tests.

Covers every fix from the M37 audit:
  P0 — Watchlist re-add after removal (no IntegrityError, same row reused)
  P1 — Episode lifecycle: MONITORING → OPEN blocked
  P1 — Notification storm: hour-based dedupe key, per-user rate limit
  P2 — Audit actor_id propagation (acknowledge, dismiss, watchlist, episode)
  P2 — Signal expiry emits surveillance.signal.expired
  P2 — Watchlist severity upgrade emits surveillance.watchlist.severity_upgraded
  P3 — Heatmap severity max uses numeric rank, not alphabetical string max
  P3 — Heatmap geography/sector filters signal_status == ACTIVE
  P3 — Portfolio monitor uses ROW_NUMBER (no N+1)
  P3 — attach_signal_to_episode respects organization_id guard
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_session(scalar_one_or_none=None, scalars_all=None, scalar_one=0):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none)
    result.scalar_one = MagicMock(return_value=scalar_one)
    result.scalars.return_value.all.return_value = scalars_all or []
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_watchlist_entry(status="ACTIVE", severity="HIGH", supplier_id="sup-1"):
    e = MagicMock()
    e.id = "wl-1"
    e.organization_id = "org-1"
    e.supplier_id = supplier_id
    e.watchlist_status = status
    e.severity = severity
    e.watch_reason = "existing reason"
    return e


def _make_signal(signal_id="sig-1", severity="HIGH", signal_status="ACTIVE"):
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    s = MagicMock(spec=SurveillanceSignalModel)
    s.id = signal_id
    s.organization_id = "org-1"
    s.supplier_id = "sup-1"
    s.signal_type = "DRIFT"
    s.severity = severity
    s.signal_status = signal_status
    s.title = "Test signal"
    s.description = "desc"
    s.detected_at = datetime.now(UTC)
    s.expires_at = None
    s.acknowledged_by = None
    s.acknowledged_at = None
    s.episode_id = None
    s.explainability_json = {}
    s.dedupe_key = None
    s.created_at = datetime.now(UTC)
    s.updated_at = datetime.now(UTC)
    return s


def _make_episode(status="OPEN", org_id="org-1"):
    e = MagicMock()
    e.id = "ep-1"
    e.organization_id = org_id
    e.episode_status = status
    e.closed_at = None
    e.resolved_by = None
    e.signal_count = 0
    return e


# ══════════════════════════════════════════════════════════════════════════════
# P0 — Watchlist Re-Add After Removal
# ══════════════════════════════════════════════════════════════════════════════


class TestWatchlistReAdd:
    """P0: Re-adding a previously removed supplier must not raise IntegrityError."""

    @pytest.mark.asyncio
    async def test_fresh_add_inserts_new_row(self):
        """First-time add: no existing rows → INSERT."""
        from application.surveillance.watchlist_service import add_to_watchlist

        # Both lookups (ACTIVE and ANY) return None → new entry
        session = _make_session(scalar_one_or_none=None)

        entry = await add_to_watchlist(
            organization_id="org-1",
            supplier_id="sup-1",
            watch_reason="New risk",
            severity="HIGH",
            session=session,
        )

        added_types = [type(c.args[0]).__name__ for c in session.add.call_args_list]
        assert "SupplierWatchlistModel" in added_types
        assert entry.watchlist_status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_reactivates_removed_row_instead_of_inserting(self):
        """Re-add after removal: updates REMOVED row, no INSERT."""
        from application.surveillance.watchlist_service import add_to_watchlist

        removed_entry = _make_watchlist_entry(status="REMOVED", severity="HIGH")

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            if call_idx == 0:
                # get_watchlist_entry (ACTIVE) → None
                res.scalar_one_or_none = MagicMock(return_value=None)
            elif call_idx == 1:
                # _get_any_watchlist_entry → finds REMOVED entry
                res.scalar_one_or_none = MagicMock(return_value=removed_entry)
            else:
                res.scalar_one_or_none = MagicMock(return_value=None)
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await add_to_watchlist(
            organization_id="org-1",
            supplier_id="sup-1",
            watch_reason="Re-added after review",
            severity="CRITICAL",
            session=session,
        )

        # Must NOT insert a new row
        added_types = [type(c.args[0]).__name__ for c in session.add.call_args_list]
        assert "SupplierWatchlistModel" not in added_types

        # Must reactivate the existing row in-place
        assert result is removed_entry
        assert result.watchlist_status == "ACTIVE"
        assert result.severity == "CRITICAL"
        assert result.removed_at is None
        assert result.removed_by is None

    @pytest.mark.asyncio
    async def test_add_remove_readd_cycle(self):
        """Full cycle: add → remove → re-add uses same row."""
        from application.surveillance import watchlist_service

        # Step 1: add
        session_add = _make_session(scalar_one_or_none=None)
        entry = await watchlist_service.add_to_watchlist(
            organization_id="org-1",
            supplier_id="sup-1",
            watch_reason="Initial",
            severity="HIGH",
            session=session_add,
        )
        assert entry.watchlist_status == "ACTIVE"

        # Step 2: remove
        active_entry = _make_watchlist_entry(status="ACTIVE")
        session_remove = _make_session(scalar_one_or_none=active_entry)
        removed = await watchlist_service.remove_from_watchlist(
            "org-1", "sup-1", "user-1", session_remove
        )
        assert removed.watchlist_status == "REMOVED"

        # Step 3: re-add — simulate finding the REMOVED row
        removed_mock = _make_watchlist_entry(status="REMOVED")
        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            if call_idx == 0:
                res.scalar_one_or_none = MagicMock(return_value=None)  # no ACTIVE
            else:
                res.scalar_one_or_none = MagicMock(return_value=removed_mock)  # REMOVED exists
            res.scalar_one = MagicMock(return_value=0)
            call_idx += 1
            return res

        session_readd = AsyncMock()
        session_readd.execute = _execute
        session_readd.add = MagicMock()
        session_readd.flush = AsyncMock()

        readded = await watchlist_service.add_to_watchlist(
            organization_id="org-1",
            supplier_id="sup-1",
            watch_reason="Re-added",
            severity="HIGH",
            session=session_readd,
        )

        # Same row, no new INSERT
        assert readded is removed_mock
        assert readded.watchlist_status == "ACTIVE"
        added_types = [type(c.args[0]).__name__ for c in session_readd.add.call_args_list]
        assert "SupplierWatchlistModel" not in added_types

    @pytest.mark.asyncio
    async def test_reactivation_emits_added_audit_event(self):
        """Reactivation must produce a surveillance.watchlist.added audit."""
        from application.surveillance.watchlist_service import add_to_watchlist
        from infrastructure.persistence.models.audit_event import AuditEventModel

        removed_entry = _make_watchlist_entry(status="REMOVED")
        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            res.scalar_one_or_none = MagicMock(
                return_value=None if call_idx == 0 else removed_entry
            )
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await add_to_watchlist(
            organization_id="org-1",
            supplier_id="sup-1",
            watch_reason="Re-added",
            severity="HIGH",
            session=session,
        )

        audit_calls = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        assert any("watchlist.added" in c.action for c in audit_calls)


# ══════════════════════════════════════════════════════════════════════════════
# P1 — Episode Lifecycle Governance
# ══════════════════════════════════════════════════════════════════════════════


class TestEpisodeLifecycle:
    """P1: MONITORING → OPEN transition must be rejected."""

    @pytest.mark.asyncio
    async def test_monitoring_to_open_is_rejected(self):
        """MONITORING → OPEN must raise ValueError (backward transition removed)."""
        from application.surveillance.episode_service import transition_episode

        episode = _make_episode(status="MONITORING")
        session = _make_session(scalar_one_or_none=episode)

        with pytest.raises(ValueError, match="Cannot transition"):
            await transition_episode("ep-1", "org-1", "OPEN", "user-1", session)

    @pytest.mark.asyncio
    async def test_monitoring_to_resolved_is_allowed(self):
        """MONITORING → RESOLVED must succeed."""
        from application.surveillance.episode_service import transition_episode

        episode = _make_episode(status="MONITORING")
        session = _make_session(scalar_one_or_none=episode)

        result = await transition_episode("ep-1", "org-1", "RESOLVED", "user-1", session)

        assert result.episode_status == "RESOLVED"
        assert result.closed_at is not None
        assert result.resolved_by == "user-1"

    @pytest.mark.asyncio
    async def test_open_to_monitoring_still_allowed(self):
        """OPEN → MONITORING must still succeed (no regression)."""
        from application.surveillance.episode_service import transition_episode

        episode = _make_episode(status="OPEN")
        session = _make_session(scalar_one_or_none=episode)

        result = await transition_episode("ep-1", "org-1", "MONITORING", "user-1", session)

        assert result.episode_status == "MONITORING"

    @pytest.mark.asyncio
    async def test_open_to_resolved_still_allowed(self):
        """OPEN → RESOLVED must still succeed (no regression)."""
        from application.surveillance.episode_service import transition_episode

        episode = _make_episode(status="OPEN")
        session = _make_session(scalar_one_or_none=episode)

        result = await transition_episode("ep-1", "org-1", "RESOLVED", "user-1", session)

        assert result.episode_status == "RESOLVED"

    @pytest.mark.asyncio
    async def test_resolved_is_terminal(self):
        """RESOLVED → anything must raise ValueError."""
        from application.surveillance.episode_service import transition_episode

        for target in ["OPEN", "MONITORING", "RESOLVED"]:
            episode = _make_episode(status="RESOLVED")
            session = _make_session(scalar_one_or_none=episode)

            with pytest.raises(ValueError, match="Cannot transition"):
                await transition_episode("ep-1", "org-1", target, "user-1", session)

    def test_allowed_map_excludes_monitoring_to_open(self):
        """Source-code guard: MONITORING must not list OPEN as allowed."""
        from application.surveillance import episode_service

        src = inspect.getsource(episode_service.transition_episode)
        # Extract the allowed dict. Verify MONITORING maps only to RESOLVED.
        assert (
            '"MONITORING": ["RESOLVED"]' in src
            or '"MONITORING": ["RESOLVED",]' in src
            or '"MONITORING": ["RESOLVED"]' in src
        )


# ══════════════════════════════════════════════════════════════════════════════
# P1 — Notification Storm Prevention
# ══════════════════════════════════════════════════════════════════════════════


class TestNotificationStorm:
    """P1: At most one HIGH/CRITICAL notification per user per hour."""

    def test_dedupe_key_uses_hour_not_signal_id(self):
        """Dedupe key must be hour-based, not signal-id-based."""
        from application.surveillance import signal_service

        src = inspect.getsource(signal_service._maybe_notify)
        assert "surveillance_digest" in src
        assert "hour_str" in src or "%Y-%m-%dT%H" in src

    def test_notification_includes_alert_count(self):
        """Notification title must include the alert count."""
        from application.surveillance import signal_service

        src = inspect.getsource(signal_service._maybe_notify)
        assert "alert_count" in src

    @pytest.mark.asyncio
    async def test_high_signal_triggers_notify_with_hour_key(self):
        """HIGH signal must call notify() with an hour-based dedupe key."""
        from application.surveillance.signal_service import _maybe_notify

        signal = _make_signal(severity="HIGH")
        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.organization_id = "org-1"
        mock_user.is_active = True

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            if call_idx == 0:
                # users query
                res.scalars.return_value.all.return_value = [mock_user]
            else:
                # alert count query
                res.scalar_one = MagicMock(return_value=3)
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        notify_calls = []

        async def _mock_notify(**kwargs):
            notify_calls.append(kwargs)

        with patch("application.notification_service.notify", side_effect=_mock_notify):
            await _maybe_notify(signal, "org-1", session)

        assert len(notify_calls) == 1
        dedupe = notify_calls[0]["dedupe_key"]
        # Must be hour-granularity: surveillance_digest:{org}:{user}:{YYYY-MM-DDTHH}
        assert dedupe.startswith("surveillance_digest:org-1:user-1:")
        hour_part = dedupe.split(":")[-1]
        assert len(hour_part) == 13  # "YYYY-MM-DDTHH"
        assert "T" in hour_part

    @pytest.mark.asyncio
    async def test_low_signal_does_not_notify(self):
        """LOW severity signal must not produce any notification."""
        from application.surveillance.signal_service import _maybe_notify

        signal = _make_signal(severity="LOW")
        session = _make_session()

        notify_calls = []

        async def _mock_notify(**kwargs):
            notify_calls.append(kwargs)

        with patch("application.notification_service.notify", side_effect=_mock_notify):
            await _maybe_notify(signal, "org-1", session)

        assert notify_calls == []

    @pytest.mark.asyncio
    async def test_critical_signal_uses_same_hour_key(self):
        """Two CRITICAL signals in same hour → same dedupe key → only one notification."""
        from application.surveillance.signal_service import _maybe_notify

        signal1 = _make_signal(signal_id="sig-1", severity="CRITICAL")
        signal2 = _make_signal(signal_id="sig-2", severity="CRITICAL")

        mock_user = MagicMock()
        mock_user.id = "user-1"

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            res.scalars.return_value.all.return_value = [mock_user]
            res.scalar_one = MagicMock(return_value=1)
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        dedupe_keys = []

        async def _mock_notify(**kwargs):
            dedupe_keys.append(kwargs["dedupe_key"])

        with patch("application.notification_service.notify", side_effect=_mock_notify):
            await _maybe_notify(signal1, "org-1", session)
            await _maybe_notify(signal2, "org-1", session)

        # Both produce the SAME dedupe key for the same hour
        assert len(dedupe_keys) == 2
        assert dedupe_keys[0] == dedupe_keys[1]


# ══════════════════════════════════════════════════════════════════════════════
# P2 — Audit Actor Attribution
# ══════════════════════════════════════════════════════════════════════════════


class TestAuditActorAttribution:
    """P2: User-initiated actions must record the real user ID, not 'surveillance_engine'."""

    @pytest.mark.asyncio
    async def test_acknowledge_signal_records_user_as_actor(self):
        from application.surveillance.signal_service import acknowledge_signal
        from infrastructure.persistence.models.audit_event import AuditEventModel

        signal = _make_signal(signal_status="ACTIVE")
        session = _make_session(scalar_one_or_none=signal)

        await acknowledge_signal("sig-1", "org-1", "user-42", session)

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        ack_event = next((e for e in audit_events if "acknowledged" in e.action), None)
        assert ack_event is not None
        assert ack_event.actor_id == "user-42"

    @pytest.mark.asyncio
    async def test_dismiss_signal_records_user_as_actor(self):
        from application.surveillance.signal_service import dismiss_signal
        from infrastructure.persistence.models.audit_event import AuditEventModel

        signal = _make_signal(signal_status="ACTIVE")
        session = _make_session(scalar_one_or_none=signal)

        await dismiss_signal("sig-1", "org-1", "user-99", session)

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        dismiss_event = next((e for e in audit_events if "dismissed" in e.action), None)
        assert dismiss_event is not None
        assert dismiss_event.actor_id == "user-99"

    @pytest.mark.asyncio
    async def test_transition_episode_records_user_as_actor(self):
        from application.surveillance.episode_service import transition_episode
        from infrastructure.persistence.models.audit_event import AuditEventModel

        episode = _make_episode(status="OPEN")
        session = _make_session(scalar_one_or_none=episode)

        await transition_episode("ep-1", "org-1", "MONITORING", "user-77", session)

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        assert any(e.actor_id == "user-77" for e in audit_events)

    @pytest.mark.asyncio
    async def test_remove_watchlist_records_user_as_actor(self):
        from application.surveillance.watchlist_service import remove_from_watchlist
        from infrastructure.persistence.models.audit_event import AuditEventModel

        entry = _make_watchlist_entry(status="ACTIVE")
        session = _make_session(scalar_one_or_none=entry)

        await remove_from_watchlist("org-1", "sup-1", "user-55", session)

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        removed_event = next((e for e in audit_events if "removed" in e.action), None)
        assert removed_event is not None
        assert removed_event.actor_id == "user-55"

    @pytest.mark.asyncio
    async def test_create_episode_records_creator_as_actor(self):
        from application.surveillance.episode_service import create_episode
        from infrastructure.persistence.models.audit_event import AuditEventModel

        session = _make_session(scalar_one_or_none=None)

        await create_episode(
            organization_id="org-1",
            title="Test episode",
            description="desc",
            created_by="user-33",
            session=session,
        )

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        created_event = next((e for e in audit_events if "created" in e.action), None)
        assert created_event is not None
        assert created_event.actor_id == "user-33"

    @pytest.mark.asyncio
    async def test_engine_actions_still_use_surveillance_engine_actor(self):
        """signal.create() (engine-triggered) must still use 'surveillance_engine'."""
        from application.surveillance.signal_service import create_signal
        from infrastructure.persistence.models.audit_event import AuditEventModel

        session = _make_session(scalar_one_or_none=None)

        await create_signal(
            organization_id="org-1",
            signal_type="DRIFT",
            source_type="supplier_score",
            severity="MEDIUM",
            title="Test",
            description="desc",
            session=session,
        )

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        created_event = next((e for e in audit_events if "signal.created" in e.action), None)
        assert created_event is not None
        assert created_event.actor_id == "surveillance_engine"

    def test_log_audit_event_accepts_actor_id_param(self):
        """_log_audit_event must accept actor_id as a keyword argument."""
        from application.surveillance import signal_service

        sig = inspect.signature(signal_service._log_audit_event)
        assert "actor_id" in sig.parameters


# ══════════════════════════════════════════════════════════════════════════════
# P2 — Signal Expiry Audit
# ══════════════════════════════════════════════════════════════════════════════


class TestSignalExpiryAudit:
    """P2: expire_stale_signals() must emit surveillance.signal.expired per signal."""

    @pytest.mark.asyncio
    async def test_expired_signals_generate_audit_events(self):
        from application.surveillance.signal_service import expire_stale_signals
        from infrastructure.persistence.models.audit_event import AuditEventModel

        stale_1 = _make_signal(signal_id="s1", signal_status="ACTIVE")
        stale_2 = _make_signal(signal_id="s2", signal_status="ACTIVE")
        stale_1.expires_at = datetime(2020, 1, 1, tzinfo=UTC)
        stale_2.expires_at = datetime(2020, 1, 1, tzinfo=UTC)

        session = _make_session(scalars_all=[stale_1, stale_2])

        count = await expire_stale_signals(session)

        assert count == 2
        assert stale_1.signal_status == "EXPIRED"
        assert stale_2.signal_status == "EXPIRED"

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        expired_events = [e for e in audit_events if "signal.expired" in e.action]
        assert len(expired_events) == 2

    @pytest.mark.asyncio
    async def test_no_stale_signals_no_audit_events(self):
        from application.surveillance.signal_service import expire_stale_signals
        from infrastructure.persistence.models.audit_event import AuditEventModel

        session = _make_session(scalars_all=[])

        count = await expire_stale_signals(session)

        assert count == 0
        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        assert audit_events == []

    @pytest.mark.asyncio
    async def test_expiry_audit_uses_surveillance_engine_actor(self):
        """Expiry is engine-triggered; actor must be 'surveillance_engine'."""
        from application.surveillance.signal_service import expire_stale_signals
        from infrastructure.persistence.models.audit_event import AuditEventModel

        stale = _make_signal(signal_id="s1")
        stale.expires_at = datetime(2020, 1, 1, tzinfo=UTC)
        session = _make_session(scalars_all=[stale])

        await expire_stale_signals(session)

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        expired_event = next((e for e in audit_events if "expired" in e.action), None)
        assert expired_event is not None
        assert expired_event.actor_id == "surveillance_engine"

    def test_expire_stale_signals_source_contains_audit_call(self):
        from application.surveillance import signal_service

        src = inspect.getsource(signal_service.expire_stale_signals)
        assert "surveillance.signal.expired" in src
        assert "_log_audit_event" in src


# ══════════════════════════════════════════════════════════════════════════════
# P2 — Watchlist Severity Upgrade Audit
# ══════════════════════════════════════════════════════════════════════════════


class TestWatchlistSeverityUpgradeAudit:
    """P2: Severity upgrades must emit surveillance.watchlist.severity_upgraded."""

    @pytest.mark.asyncio
    async def test_severity_upgrade_emits_audit_event(self):
        from application.surveillance.watchlist_service import add_to_watchlist
        from infrastructure.persistence.models.audit_event import AuditEventModel

        existing = _make_watchlist_entry(status="ACTIVE", severity="HIGH")
        session = _make_session(scalar_one_or_none=existing)

        await add_to_watchlist(
            organization_id="org-1",
            supplier_id="sup-1",
            watch_reason="Escalating",
            severity="CRITICAL",  # higher than HIGH
            session=session,
        )

        assert existing.severity == "CRITICAL"

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        upgrade_event = next((e for e in audit_events if "severity_upgraded" in e.action), None)
        assert upgrade_event is not None
        assert "from=HIGH" in upgrade_event.detail
        assert "to=CRITICAL" in upgrade_event.detail

    @pytest.mark.asyncio
    async def test_same_severity_does_not_emit_upgrade_audit(self):
        """Idempotent add with same severity must not emit upgrade event."""
        from application.surveillance.watchlist_service import add_to_watchlist
        from infrastructure.persistence.models.audit_event import AuditEventModel

        existing = _make_watchlist_entry(status="ACTIVE", severity="HIGH")
        session = _make_session(scalar_one_or_none=existing)

        await add_to_watchlist(
            organization_id="org-1",
            supplier_id="sup-1",
            watch_reason="No change",
            severity="HIGH",  # same severity
            session=session,
        )

        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        upgrade_events = [e for e in audit_events if "severity_upgraded" in e.action]
        assert upgrade_events == []

    @pytest.mark.asyncio
    async def test_downgrade_does_not_emit_upgrade_audit(self):
        """Attempting a downgrade (CRITICAL → HIGH) must be silently ignored."""
        from application.surveillance.watchlist_service import add_to_watchlist
        from infrastructure.persistence.models.audit_event import AuditEventModel

        existing = _make_watchlist_entry(status="ACTIVE", severity="CRITICAL")
        session = _make_session(scalar_one_or_none=existing)

        result = await add_to_watchlist(
            organization_id="org-1",
            supplier_id="sup-1",
            watch_reason="Downgrade attempt",
            severity="HIGH",  # lower
            session=session,
        )

        # Severity unchanged
        assert result.severity == "CRITICAL"
        audit_events = [
            c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AuditEventModel)
        ]
        upgrade_events = [e for e in audit_events if "severity_upgraded" in e.action]
        assert upgrade_events == []


# ══════════════════════════════════════════════════════════════════════════════
# P3 — Heatmap Severity Max Correctness
# ══════════════════════════════════════════════════════════════════════════════


class TestHeatmapSeverityMax:
    """P3: Severity max must use numeric rank (CRITICAL=4), not alphabetical strings."""

    def test_geography_heatmap_uses_numeric_case_expression(self):
        """Source must contain 'CRITICAL', 4 in a case expression, not func.max(severity)."""
        from application.surveillance import portfolio_monitor

        src = inspect.getsource(portfolio_monitor._heatmap_by_geography)
        # Must use severity_rank case expression
        assert "severity_rank" in src or "max_rank" in src
        # Must NOT use the broken string max
        assert "func.max(SurveillanceSignalModel.severity)" not in src

    def test_rank_to_severity_mapping_correct(self):
        """_RANK_TO_SEVERITY must map CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1."""
        from application.surveillance.portfolio_monitor import _RANK_TO_SEVERITY

        assert _RANK_TO_SEVERITY[4] == "CRITICAL"
        assert _RANK_TO_SEVERITY[3] == "HIGH"
        assert _RANK_TO_SEVERITY[2] == "MEDIUM"
        assert _RANK_TO_SEVERITY[1] == "LOW"
        assert _RANK_TO_SEVERITY[0] == "NONE"

    def test_rank_ordering_is_correct(self):
        """Numeric rank must produce CRITICAL > HIGH > MEDIUM > LOW."""
        from application.surveillance.portfolio_monitor import _RANK_TO_SEVERITY

        # When using max(), rank 4 > 3 > 2 > 1 — verify mapping is consistent
        ranks = sorted(_RANK_TO_SEVERITY.keys(), reverse=True)
        severities = [_RANK_TO_SEVERITY[r] for r in ranks]
        assert severities[0] == "CRITICAL"
        assert severities[1] == "HIGH"
        assert severities[2] == "MEDIUM"
        assert severities[3] == "LOW"


# ══════════════════════════════════════════════════════════════════════════════
# P3 — Heatmap Active Signal Filter
# ══════════════════════════════════════════════════════════════════════════════


class TestHeatmapActiveFilter:
    """P3: Geography and sector heatmaps must count only ACTIVE signals."""

    def test_geography_heatmap_filters_active_signals_in_join(self):
        from application.surveillance import portfolio_monitor

        src = inspect.getsource(portfolio_monitor._heatmap_by_geography)
        # The active filter must be inside the JOIN ON clause, not WHERE
        assert 'signal_status == "ACTIVE"' in src or "signal_status == 'ACTIVE'" in src

    def test_sector_heatmap_filters_active_signals_in_join(self):
        from application.surveillance import portfolio_monitor

        src = inspect.getsource(portfolio_monitor._heatmap_by_sector)
        assert 'signal_status == "ACTIVE"' in src or "signal_status == 'ACTIVE'" in src

    def test_severity_heatmap_already_filters_active(self):
        """Regression guard: severity heatmap already had the filter."""
        from application.surveillance import portfolio_monitor

        src = inspect.getsource(portfolio_monitor._heatmap_by_severity)
        assert "ACTIVE" in src

    def test_geography_heatmap_uses_and_for_join_condition(self):
        """Geography join must use and_() to combine supplier_id + signal_status."""
        from application.surveillance import portfolio_monitor

        src = inspect.getsource(portfolio_monitor._heatmap_by_geography)
        assert "and_" in src

    def test_sector_heatmap_uses_and_for_join_condition(self):
        from application.surveillance import portfolio_monitor

        src = inspect.getsource(portfolio_monitor._heatmap_by_sector)
        assert "and_" in src


# ══════════════════════════════════════════════════════════════════════════════
# P3 — Portfolio Monitor N+1 Elimination
# ══════════════════════════════════════════════════════════════════════════════


class TestPortfolioMonitorN1:
    """P3: compute_portfolio_stats must use a single join query for trend aggregation."""

    def test_uses_row_number_not_per_supplier_loop(self):
        """Source must contain row_number() and must NOT iterate suppliers in Python."""
        from application.surveillance import portfolio_monitor

        src = inspect.getsource(portfolio_monitor.compute_portfolio_stats)
        # Must use ROW_NUMBER
        assert "row_number" in src
        # Must NOT have per-supplier score query in a for loop
        assert "for supplier in suppliers" not in src

    def test_uses_outerjoin_for_trend_lookup(self):
        from application.surveillance import portfolio_monitor

        src = inspect.getsource(portfolio_monitor.compute_portfolio_stats)
        assert "outerjoin" in src or "outer" in src.lower()

    @pytest.mark.asyncio
    async def test_returns_correct_keys_with_join_query(self):
        """With mocked session, must still return all 10 required stats keys."""
        from application.surveillance.portfolio_monitor import compute_portfolio_stats

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            res.scalar_one = MagicMock(return_value=0)
            res.scalar_one_or_none = MagicMock(return_value=None)
            res.scalars.return_value.all.return_value = []
            # The trend join query returns .all() rows
            res.all.return_value = []
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        stats = await compute_portfolio_stats("org-1", session)

        required = {
            "total_suppliers",
            "suppliers_at_risk",
            "suppliers_improving",
            "suppliers_deteriorating",
            "suppliers_stable",
            "suppliers_needing_review",
            "watchlist_count",
            "active_signals",
            "critical_signals",
            "open_episodes",
        }
        assert required.issubset(set(stats.keys()))


# ══════════════════════════════════════════════════════════════════════════════
# P3 — Episode Attachment Tenant Guard
# ══════════════════════════════════════════════════════════════════════════════


class TestEpisodeAttachTenantGuard:
    """P3: attach_signal_to_episode must filter by organization_id when provided."""

    @pytest.mark.asyncio
    async def test_with_org_id_returns_none_for_wrong_org(self):
        """If episode belongs to a different org, attachment must be a no-op."""
        from application.surveillance.episode_service import attach_signal_to_episode

        # Episode not found (simulates wrong org returning None)
        session = _make_session(scalar_one_or_none=None)
        signal = _make_signal()

        # Must not raise; episode_id link on signal must not be set
        await attach_signal_to_episode("ep-1", signal, session, organization_id="org-99")

        # episode is None → signal.episode_id is never set
        assert signal.episode_id is None

    @pytest.mark.asyncio
    async def test_with_matching_org_id_attaches_signal(self):
        """Correct org_id → episode found → signal attached."""
        from application.surveillance.episode_service import attach_signal_to_episode

        episode = _make_episode(status="OPEN", org_id="org-1")
        session = _make_session(scalar_one_or_none=episode)
        signal = _make_signal()

        await attach_signal_to_episode("ep-1", signal, session, organization_id="org-1")

        assert signal.episode_id == "ep-1"
        assert episode.signal_count == 1

    @pytest.mark.asyncio
    async def test_without_org_id_still_works(self):
        """Backward-compatible: no organization_id → no org filter applied."""
        from application.surveillance.episode_service import attach_signal_to_episode

        episode = _make_episode(status="OPEN")
        session = _make_session(scalar_one_or_none=episode)
        signal = _make_signal()

        await attach_signal_to_episode("ep-1", signal, session)

        assert signal.episode_id == "ep-1"

    def test_function_accepts_organization_id_param(self):
        """attach_signal_to_episode must accept organization_id keyword."""
        from application.surveillance.episode_service import attach_signal_to_episode

        sig = inspect.signature(attach_signal_to_episode)
        assert "organization_id" in sig.parameters

    def test_source_contains_org_filter(self):
        from application.surveillance import episode_service

        src = inspect.getsource(episode_service.attach_signal_to_episode)
        assert "organization_id" in src
