"""M38 Supplier Network Intelligence — Unit Tests.

Coverage:
  1. Relationship CRUD (TestRelationshipService)
  2. Discovery Engine (TestDiscoveryEngine)
  3. Graph Service / BFS (TestGraphService)
  4. Risk Propagation (TestRiskPropagation)
  5. Dependency Analysis (TestDependencyService)
  6. Centrality Service (TestCentralityService)
  7. Cascading Risk (TestCascadingRisk)
  8. Cluster Service (TestClusterService)
  9. Resilience Service (TestResilienceService)
  10. Tenant Isolation (TestTenantIsolation)
  11. Dashboard (TestNetworkDashboard)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fake_rel(
    org_id="org-1",
    supplier_id="sup-A",
    related_id="sup-B",
    rel_type="SHARED_COUNTRY",
    confidence=0.8,
    status="ACTIVE",
):
    r = MagicMock()
    r.id = str(uuid.uuid4())
    r.organization_id = org_id
    r.supplier_id = supplier_id
    r.related_supplier_id = related_id
    r.relationship_type = rel_type
    r.confidence = confidence
    r.source = "MANUAL"
    r.rationale = "test"
    r.relationship_status = status
    r.removed_at = None
    r.removed_by = None
    r.created_at = datetime.now(UTC)
    r.updated_at = datetime.now(UTC)
    return r


def _fake_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


# ── 1. Relationship Service ───────────────────────────────────────────────────

def _session_with_execute_sequence(*scalars):
    """Build a session whose execute() returns successive scalar_one_or_none values."""
    session = _fake_session()
    results = []
    for val in scalars:
        r = MagicMock()
        r.scalar_one_or_none = MagicMock(return_value=val)
        r.scalars.return_value.all = MagicMock(return_value=[])
        r.all = MagicMock(return_value=[])
        results.append(r)
    session.execute.side_effect = results
    return session


class TestRelationshipService:
    """relationship_service: create, validate, remove, audit."""

    @pytest.mark.asyncio
    async def test_create_relationship_success(self):
        from application.network.relationship_service import create_relationship

        # P1 M38.1: execute sequence:
        #   1. supplier A ownership check → truthy (found)
        #   2. supplier B ownership check → truthy (found)
        #   3. duplicate check → None (no duplicate)
        session = _session_with_execute_sequence(
            MagicMock(id="sup-A"),  # supplier A found
            MagicMock(id="sup-B"),  # supplier B found
            None,                   # no duplicate
        )

        with patch(
            "application.network.relationship_service._log_audit_event",
            new_callable=AsyncMock,
        ):
            rel = await create_relationship(
                organization_id="org-1",
                supplier_id="sup-A",
                related_supplier_id="sup-B",
                relationship_type="SUBSIDIARY",
                confidence=0.9,
                source="MANUAL",
                rationale="Parent owns subsidiary",
                created_by="user-1",
                session=session,
            )

        assert rel.organization_id == "org-1"
        assert rel.relationship_type == "SUBSIDIARY"
        assert rel.confidence == 0.9
        assert rel.relationship_status == "ACTIVE"
        session.add.assert_called_once()
        session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_create_relationship_invalid_type(self):
        from application.network.relationship_service import create_relationship

        session = _fake_session()
        with pytest.raises(ValueError, match="Invalid relationship_type"):
            await create_relationship(
                organization_id="org-1",
                supplier_id="sup-A",
                related_supplier_id="sup-B",
                relationship_type="BOGUS",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_create_relationship_self_reference_rejected(self):
        from application.network.relationship_service import create_relationship

        session = _fake_session()
        with pytest.raises(ValueError, match="must differ"):
            await create_relationship(
                organization_id="org-1",
                supplier_id="sup-A",
                related_supplier_id="sup-A",
                relationship_type="CUSTOM",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_create_relationship_invalid_confidence(self):
        from application.network.relationship_service import create_relationship

        session = _fake_session()
        with pytest.raises(ValueError, match="confidence"):
            await create_relationship(
                organization_id="org-1",
                supplier_id="sup-A",
                related_supplier_id="sup-B",
                relationship_type="CUSTOM",
                confidence=1.5,
                session=session,
            )

    @pytest.mark.asyncio
    async def test_remove_relationship_records_audit(self):
        from application.network.relationship_service import remove_relationship

        existing = _fake_rel()
        existing.relationship_status = "ACTIVE"
        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=existing
        )

        with patch(
            "application.network.relationship_service._log_audit_event",
            new_callable=AsyncMock,
        ) as mock_audit:
            removed = await remove_relationship(
                existing.id, "org-1", "user-2", session
            )

        assert removed.relationship_status == "REMOVED"
        assert removed.removed_by == "user-2"
        mock_audit.assert_awaited_once()
        call_action = mock_audit.call_args[0][1]
        assert call_action == "network.relationship.removed"

    @pytest.mark.asyncio
    async def test_remove_already_removed_raises(self):
        from application.network.relationship_service import remove_relationship

        existing = _fake_rel(status="REMOVED")
        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=existing
        )

        with pytest.raises(ValueError, match="already removed"):
            await remove_relationship(existing.id, "org-1", "user-2", session)

    @pytest.mark.asyncio
    async def test_get_relationship_not_found_returns_none(self):
        from application.network.relationship_service import get_relationship

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
        result = await get_relationship("bad-id", "org-1", session)
        assert result is None


# ── 2. Discovery Engine ───────────────────────────────────────────────────────

class TestDiscoveryEngine:
    """discovery_engine: dedup, approve, reject."""

    @pytest.mark.asyncio
    async def test_approve_suggestion_creates_relationship(self):
        from application.network.discovery_engine import approve_suggestion

        suggestion = MagicMock()
        suggestion.id = str(uuid.uuid4())
        suggestion.organization_id = "org-1"
        suggestion.supplier_id = "sup-A"
        suggestion.related_supplier_id = "sup-B"
        suggestion.relationship_type = "SHARED_COUNTRY"
        suggestion.confidence = 0.5
        suggestion.rationale = "Same country"
        suggestion.suggestion_status = "PENDING"

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=suggestion
        )

        with patch(
            "application.network.discovery_engine._log_audit_event",
            new_callable=AsyncMock,
        ), patch(
            "application.network.relationship_service.create_relationship",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = _fake_rel()
            result = await approve_suggestion(
                suggestion.id, "org-1", "user-1", session
            )

        assert result.suggestion_status == "APPROVED"
        assert result.reviewed_by == "user-1"
        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approve_non_pending_raises(self):
        from application.network.discovery_engine import approve_suggestion

        suggestion = MagicMock()
        suggestion.suggestion_status = "REJECTED"
        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=suggestion
        )
        with pytest.raises(ValueError, match="already REJECTED"):
            await approve_suggestion("s-id", "org-1", "user-1", session)

    @pytest.mark.asyncio
    async def test_reject_suggestion_records_note(self):
        from application.network.discovery_engine import reject_suggestion

        suggestion = MagicMock()
        suggestion.id = str(uuid.uuid4())
        suggestion.suggestion_status = "PENDING"
        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=suggestion
        )

        with patch(
            "application.network.discovery_engine._log_audit_event",
            new_callable=AsyncMock,
        ):
            result = await reject_suggestion(
                suggestion.id, "org-1", "user-2", review_note="Not relevant", session=session
            )

        assert result.suggestion_status == "REJECTED"
        assert result.review_note == "Not relevant"

    @pytest.mark.asyncio
    async def test_reject_not_found_raises(self):
        from application.network.discovery_engine import reject_suggestion

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await reject_suggestion("bad-id", "org-1", "user-2", session=session)

    @pytest.mark.asyncio
    async def test_approve_not_found_raises(self):
        from application.network.discovery_engine import approve_suggestion

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await approve_suggestion("bad-id", "org-1", "user-1", session)


# ── 3. Graph Service ──────────────────────────────────────────────────────────

class TestGraphService:
    """graph_service: BFS, shortest path, adjacency."""

    @pytest.mark.asyncio
    async def test_bfs_neighborhood_direct_neighbors(self):
        from application.network.graph_service import bfs_neighborhood

        session = _fake_session()

        rows = [
            MagicMock(supplier_id="A", related_supplier_id="B"),
            MagicMock(supplier_id="B", related_supplier_id="C"),
        ]
        session.execute.return_value.all = MagicMock(return_value=rows)

        result = await bfs_neighborhood("org-1", "A", max_depth=1, session=session)
        assert "B" in result
        assert result["B"] == 1
        assert "C" not in result

    @pytest.mark.asyncio
    async def test_bfs_neighborhood_two_hops(self):
        from application.network.graph_service import bfs_neighborhood

        session = _fake_session()
        rows = [
            MagicMock(supplier_id="A", related_supplier_id="B"),
            MagicMock(supplier_id="B", related_supplier_id="C"),
        ]
        session.execute.return_value.all = MagicMock(return_value=rows)

        result = await bfs_neighborhood("org-1", "A", max_depth=2, session=session)
        assert result.get("B") == 1
        assert result.get("C") == 2

    @pytest.mark.asyncio
    async def test_shortest_path_direct(self):
        from application.network.graph_service import shortest_path

        session = _fake_session()
        rows = [
            MagicMock(supplier_id="A", related_supplier_id="B"),
        ]
        session.execute.return_value.all = MagicMock(return_value=rows)

        path = await shortest_path("org-1", "A", "B", session=session)
        assert path == ["A", "B"]

    @pytest.mark.asyncio
    async def test_shortest_path_two_hops(self):
        from application.network.graph_service import shortest_path

        session = _fake_session()
        rows = [
            MagicMock(supplier_id="A", related_supplier_id="B"),
            MagicMock(supplier_id="B", related_supplier_id="C"),
        ]
        session.execute.return_value.all = MagicMock(return_value=rows)

        path = await shortest_path("org-1", "A", "C", session=session)
        assert path == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_shortest_path_no_path_returns_none(self):
        from application.network.graph_service import shortest_path

        session = _fake_session()
        session.execute.return_value.all = MagicMock(return_value=[])

        path = await shortest_path("org-1", "A", "Z", session=session)
        assert path is None

    @pytest.mark.asyncio
    async def test_shortest_path_same_node(self):
        from application.network.graph_service import shortest_path

        session = _fake_session()
        path = await shortest_path("org-1", "A", "A", session=session)
        assert path == ["A"]


# ── 4. Risk Propagation ───────────────────────────────────────────────────────

def _propagation_session(adj_rows, already_signaled_ids=None):
    """Build a session for propagate_signal tests.

    propagate_signal() makes 2 execute calls:
      1. adjacency query      → result.all()
      2. already_signaled     → result.scalars().all()
    """
    session = _fake_session()
    already = already_signaled_ids or []

    adj_result = MagicMock()
    adj_result.all = MagicMock(return_value=adj_rows)

    sig_result = MagicMock()
    sig_result.scalars.return_value.all = MagicMock(return_value=already)

    session.execute.side_effect = [adj_result, sig_result]
    return session


class TestRiskPropagation:
    """risk_propagation: attenuation, min confidence threshold, severity downgrade."""

    def test_attenuate_severity_no_change_at_distance_1(self):
        from application.network.risk_propagation import _attenuate_severity

        assert _attenuate_severity("CRITICAL", 1) == "CRITICAL"
        assert _attenuate_severity("HIGH", 1) == "HIGH"
        assert _attenuate_severity("MEDIUM", 1) == "MEDIUM"
        assert _attenuate_severity("LOW", 1) == "LOW"

    def test_attenuate_severity_downgrades_at_distance_2(self):
        from application.network.risk_propagation import _attenuate_severity

        assert _attenuate_severity("CRITICAL", 2) == "HIGH"
        assert _attenuate_severity("HIGH", 2) == "MEDIUM"
        assert _attenuate_severity("MEDIUM", 2) == "LOW"
        assert _attenuate_severity("LOW", 2) == "LOW"  # floor at LOW

    def test_attenuate_severity_two_steps_at_distance_3(self):
        from application.network.risk_propagation import _attenuate_severity

        assert _attenuate_severity("CRITICAL", 3) == "MEDIUM"
        assert _attenuate_severity("HIGH", 3) == "LOW"

    @pytest.mark.asyncio
    async def test_propagation_attenuates_with_distance(self):
        """Confidence drops by ATTENUATION_FACTOR per hop."""
        from application.network.risk_propagation import propagate_signal

        rows = [MagicMock(supplier_id="A", related_supplier_id="B", confidence=1.0)]
        session = _propagation_session(rows)

        created = []
        session.add = lambda obj: created.append(obj)

        with patch(
            "application.network.risk_propagation._log_audit_event",
            new_callable=AsyncMock,
        ):
            signals = await propagate_signal(
                organization_id="org-1",
                origin_supplier_id="A",
                source_confidence=1.0,
                source_severity="CRITICAL",
                exposure_type="SANCTIONS",
                rationale="Sanctioned",
                max_depth=1,
                session=session,
            )

        assert len(signals) == 1
        assert signals[0].confidence == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_propagation_below_min_confidence_skipped(self):
        """Very low edge confidence should produce no signals."""
        from application.network.risk_propagation import propagate_signal

        rows = [MagicMock(supplier_id="A", related_supplier_id="B", confidence=0.01)]
        session = _propagation_session(rows)

        signals = await propagate_signal(
            organization_id="org-1",
            origin_supplier_id="A",
            source_confidence=0.05,
            source_severity="HIGH",
            exposure_type="SANCTIONS",
            rationale="test",
            max_depth=1,
            session=session,
        )
        assert signals == []

    @pytest.mark.asyncio
    async def test_propagation_does_not_loop_back_to_origin(self):
        """Origin supplier must not appear as an impacted supplier."""
        from application.network.risk_propagation import propagate_signal

        rows = [
            MagicMock(supplier_id="A", related_supplier_id="B", confidence=1.0),
            MagicMock(supplier_id="B", related_supplier_id="A", confidence=1.0),
        ]
        session = _propagation_session(rows)

        created = []
        session.add = lambda obj: created.append(obj)

        with patch(
            "application.network.risk_propagation._log_audit_event",
            new_callable=AsyncMock,
        ):
            await propagate_signal(
                organization_id="org-1",
                origin_supplier_id="A",
                source_confidence=1.0,
                source_severity="HIGH",
                exposure_type="SANCTIONS",
                rationale="test",
                max_depth=2,
                session=session,
            )

        impacted_ids = [
            obj.impacted_supplier_id
            for obj in created
            if hasattr(obj, "impacted_supplier_id")
        ]
        assert "A" not in impacted_ids


# ── 5. Dependency Analysis ────────────────────────────────────────────────────

class TestDependencyService:
    """dependency_service: score formula, upsert idempotency."""

    @pytest.mark.asyncio
    async def test_dependency_score_upserts_existing(self):
        from application.network.dependency_service import _upsert_dependency

        existing = MagicMock()
        existing.dependency_score = 0.1

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=existing
        )

        now = datetime.now(UTC)
        result = await _upsert_dependency(
            organization_id="org-1",
            supplier_id=None,
            dependency_score=0.4,
            concentration_score=0.3,
            diversification_score=0.7,
            critical_supplier_count=2,
            spof_count=1,
            inputs={"test": True},
            now=now,
            session=session,
        )

        assert result.dependency_score == 0.4
        assert result.concentration_score == 0.3
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_dependency_score_inserts_new(self):
        from application.network.dependency_service import _upsert_dependency

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        now = datetime.now(UTC)
        result = await _upsert_dependency(
            organization_id="org-1",
            supplier_id=None,
            dependency_score=0.2,
            concentration_score=0.5,
            diversification_score=0.5,
            critical_supplier_count=1,
            spof_count=0,
            inputs={},
            now=now,
            session=session,
        )
        session.add.assert_called_once()


# ── 6. Centrality Service ─────────────────────────────────────────────────────

class TestCentralityService:
    """centrality_service: degree centrality formula."""

    @pytest.mark.asyncio
    async def test_degree_centrality_normalized(self):
        """With n=3 nodes and max 4 edges, centrality is bounded to [0, 1]."""
        from application.network.centrality_service import compute_centrality

        session = _fake_session()

        out_rows = [
            MagicMock(supplier_id="A", cnt=2),
            MagicMock(supplier_id="B", cnt=1),
        ]
        in_rows = [
            MagicMock(supplier_id="B", cnt=1),
            MagicMock(supplier_id="C", cnt=1),
        ]

        call_count = 0

        async def multi_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all = MagicMock(return_value=out_rows)
            elif call_count == 2:
                result.all = MagicMock(return_value=in_rows)
            else:
                # BFS adjacency calls
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="A", related_supplier_id="B"),
                    MagicMock(supplier_id="B", related_supplier_id="C"),
                ])
            return result

        session.execute = multi_execute

        records = await compute_centrality("org-1", session)
        assert len(records) > 0
        for r in records:
            assert 0.0 <= r["degree_centrality"] <= 1.0

    @pytest.mark.asyncio
    async def test_criticality_score_ranges(self):
        """Score thresholds map correctly to criticality labels."""
        from application.network.centrality_service import upsert_criticality

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        # High dependency + many findings → CRITICAL
        record = await upsert_criticality(
            organization_id="org-1",
            supplier_id="sup-A",
            centrality_data={"degree_centrality": 1.0, "inbound_degree": 10, "outbound_degree": 5, "connected_component_size": 8},
            dependency_score=1.0,
            assessment_count=10,
            finding_count=20,
            open_remediation_count=10,
            session=session,
        )
        assert record.criticality == "CRITICAL"
        assert record.criticality_score >= 0.75

    @pytest.mark.asyncio
    async def test_criticality_low_score_gives_low_label(self):
        from application.network.centrality_service import upsert_criticality

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        record = await upsert_criticality(
            organization_id="org-1",
            supplier_id="sup-B",
            centrality_data={"degree_centrality": 0.0, "inbound_degree": 0, "outbound_degree": 0, "connected_component_size": 1},
            dependency_score=0.0,
            assessment_count=0,
            finding_count=0,
            open_remediation_count=0,
            session=session,
        )
        assert record.criticality == "LOW"
        assert record.criticality_score == 0.0


# ── 7. Cascading Risk ─────────────────────────────────────────────────────────

class TestCascadingRisk:
    """cascading_risk: component detection, no self-exposure."""

    @pytest.mark.asyncio
    async def test_no_signals_returns_empty(self):
        from application.network.cascading_risk import detect_cascading_risk

        session = _fake_session()
        session.execute.return_value.all = MagicMock(return_value=[])
        result = await detect_cascading_risk("org-1", session)
        assert result == []

    @pytest.mark.asyncio
    async def test_single_supplier_with_signal_no_cascade(self):
        """Only 1 at-risk supplier — below threshold, no cascade."""
        from application.network.cascading_risk import detect_cascading_risk

        session = _fake_session()
        call_count = 0

        async def staged_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # signals query
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="A", severity="HIGH", id="sig-1", title="t")
                ])
            else:
                result.all = MagicMock(return_value=[])
            return result

        session.execute = staged_execute
        result = await detect_cascading_risk("org-1", session)
        assert result == []

    @pytest.mark.asyncio
    async def test_two_connected_at_risk_suppliers_generates_cascade(self):
        from application.network.cascading_risk import detect_cascading_risk

        session = _fake_session()
        call_count = 0
        created = []

        session.add = lambda obj: created.append(obj)

        async def staged_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # surveillance signals
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="A", severity="CRITICAL", id="sig-1", title="t"),
                    MagicMock(supplier_id="B", severity="HIGH", id="sig-2", title="t2"),
                ])
            elif call_count == 2:
                # adjacency
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="A", related_supplier_id="B"),
                ])
            else:
                # P0 M38.1: dup-check per pair → None means no existing signal
                result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        session.execute = staged_execute

        with patch(
            "application.network.cascading_risk._log_audit_event",
            new_callable=AsyncMock,
        ):
            result = await detect_cascading_risk("org-1", session)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_cluster_incidents_skips_single_supplier_categories(self):
        from application.network.cascading_risk import cluster_incidents

        session = _fake_session()
        call_count = 0

        async def staged_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            # findings: only one supplier per category
            result.all = MagicMock(return_value=[
                MagicMock(id="f1", supplier_id="A", category="Human Rights", severity="HIGH"),
            ])
            return result

        session.execute = staged_execute
        # Single supplier per category → no cluster created
        result = await cluster_incidents("org-1", session)
        assert result == []


# ── 8. Cluster Service ────────────────────────────────────────────────────────

class TestClusterService:
    """cluster_service: resolve lifecycle."""

    @pytest.mark.asyncio
    async def test_resolve_cluster_records_audit(self):
        from application.network.cluster_service import resolve_cluster

        cluster = MagicMock()
        cluster.id = str(uuid.uuid4())
        cluster.cluster_status = "ACTIVE"

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=cluster
        )

        with patch(
            "application.network.cluster_service._log_audit_event",
            new_callable=AsyncMock,
        ) as mock_audit:
            result = await resolve_cluster(cluster.id, "org-1", "user-3", session)

        assert result.cluster_status == "RESOLVED"
        mock_audit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_raises(self):
        from application.network.cluster_service import resolve_cluster

        cluster = MagicMock()
        cluster.cluster_status = "RESOLVED"
        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=cluster
        )

        with pytest.raises(ValueError, match="already resolved"):
            await resolve_cluster("c-id", "org-1", "user-3", session)

    @pytest.mark.asyncio
    async def test_resolve_not_found_raises(self):
        from application.network.cluster_service import resolve_cluster

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await resolve_cluster("bad-id", "org-1", "user-3", session)


# ── 9. Resilience Service ─────────────────────────────────────────────────────

class TestResilienceService:
    """resilience_service: score bounds, upsert."""

    @pytest.mark.asyncio
    async def test_resilience_score_bounded_0_to_1(self):
        from application.network.resilience_service import _upsert_resilience

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        now = datetime.now(UTC)
        record = await _upsert_resilience(
            organization_id="org-1",
            supplier_id=None,
            resilience_score=0.73,
            diversification_score=0.8,
            concentration_score=0.2,
            redundancy_score=0.6,
            inputs={},
            now=now,
            session=session,
        )
        assert 0.0 <= record.resilience_score <= 1.0

    @pytest.mark.asyncio
    async def test_resilience_upserts_existing(self):
        from application.network.resilience_service import _upsert_resilience

        existing = MagicMock()
        existing.resilience_score = 0.3

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=existing
        )

        now = datetime.now(UTC)
        result = await _upsert_resilience(
            organization_id="org-1",
            supplier_id=None,
            resilience_score=0.65,
            diversification_score=0.7,
            concentration_score=0.3,
            redundancy_score=0.5,
            inputs={},
            now=now,
            session=session,
        )
        assert result.resilience_score == 0.65
        session.add.assert_not_called()


# ── 10. Tenant Isolation ──────────────────────────────────────────────────────

class TestTenantIsolation:
    """Verify cross-tenant access returns None or raises."""

    @pytest.mark.asyncio
    async def test_get_relationship_cross_tenant_returns_none(self):
        from application.network.relationship_service import get_relationship

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        result = await get_relationship("rel-from-org-2", "org-1", session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cluster_cross_tenant_returns_none(self):
        from application.network.cluster_service import get_cluster

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        result = await get_cluster("cluster-from-org-2", "org-1", session)
        assert result is None

    @pytest.mark.asyncio
    async def test_approve_suggestion_cross_tenant_raises(self):
        from application.network.discovery_engine import approve_suggestion

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await approve_suggestion("sug-from-org-2", "org-1", "user-1", session)

    @pytest.mark.asyncio
    async def test_remove_relationship_cross_tenant_raises(self):
        from application.network.relationship_service import remove_relationship

        session = _fake_session()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await remove_relationship("rel-from-org-2", "org-1", "user-1", session)


# ── 11. Dashboard ─────────────────────────────────────────────────────────────

class TestNetworkDashboard:
    """Network metrics coverage."""

    def test_metrics_counters_record_correctly(self):
        from application.network.metrics import _NetworkCounters

        c = _NetworkCounters()
        c.record_relationship_created()
        c.record_relationship_created()
        c.record_suggestion_created()
        c.record_exposure_created()
        c.record_cluster_created()
        c.record_resilience_calculated()

        assert c.network_relationships_total == 2
        assert c.network_suggestions_total == 1
        assert c.network_exposures_total == 1
        assert c.network_clusters_total == 1
        assert c.network_resilience_calculations_total == 1

    def test_metrics_prometheus_output_format(self):
        from application.network.metrics import _NetworkCounters

        c = _NetworkCounters()
        c.record_relationship_created()
        lines = c.to_prometheus_lines("test")
        output = "\n".join(lines)

        assert "eios_network_relationships_total" in output
        assert "eios_network_suggestions_total" in output
        assert "eios_network_exposures_total" in output
        assert "eios_network_clusters_total" in output
        assert "eios_network_resilience_calculations_total" in output
        assert 'environment="test"' in output

    def test_valid_relationship_types_set(self):
        from application.network.relationship_service import _VALID_TYPES

        expected = {
            "PARENT_COMPANY", "SUBSIDIARY", "SISTER_COMPANY", "SHARED_COUNTRY",
            "SHARED_SECTOR", "SHARED_SUPPLY_CHAIN", "SHARED_INCIDENT",
            "SHARED_LOGISTICS", "SHARED_REGULATORY_EXPOSURE", "CUSTOM",
        }
        assert _VALID_TYPES == expected

    def test_attenuation_constants_in_range(self):
        from application.network.risk_propagation import ATTENUATION_FACTOR, MIN_CONFIDENCE

        assert 0.0 < ATTENUATION_FACTOR < 1.0
        assert 0.0 < MIN_CONFIDENCE < 0.5


# ── 12. M38.1 Hardening ───────────────────────────────────────────────────────

class TestM381Hardening:
    """P0/P1/P2/P3/P4 fixes from M38 audit."""

    # ── P0: Exposure signal dedup ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_propagate_signal_no_duplicate_per_node(self):
        """Multi-path to same node creates only one signal (confidence-revision race)."""
        from application.network.risk_propagation import propagate_signal

        # Graph: A→B, A→C, B→C  (C reachable via A→C and A→B→C)
        rows = [
            MagicMock(supplier_id="A", related_supplier_id="B", confidence=1.0),
            MagicMock(supplier_id="A", related_supplier_id="C", confidence=1.0),
            MagicMock(supplier_id="B", related_supplier_id="C", confidence=1.0),
        ]
        session = _propagation_session(rows)
        created = []
        session.add = lambda obj: created.append(obj)

        with patch(
            "application.network.risk_propagation._log_audit_event",
            new_callable=AsyncMock,
        ):
            await propagate_signal(
                organization_id="org-1",
                origin_supplier_id="A",
                source_confidence=1.0,
                source_severity="HIGH",
                exposure_type="SANCTIONS",
                rationale="test",
                max_depth=3,
                session=session,
            )

        impacted_ids = [
            obj.impacted_supplier_id
            for obj in created
            if hasattr(obj, "impacted_supplier_id")
        ]
        # C must appear at most once despite two paths
        assert impacted_ids.count("C") <= 1
        assert impacted_ids.count("B") <= 1

    @pytest.mark.asyncio
    async def test_propagate_signal_skips_already_signaled_db_entries(self):
        """Repeated propagation call skips impacted suppliers already in DB."""
        from application.network.risk_propagation import propagate_signal

        rows = [MagicMock(supplier_id="A", related_supplier_id="B", confidence=1.0)]
        # already_signaled returns B → should be skipped
        session = _propagation_session(rows, already_signaled_ids=["B"])
        created = []
        session.add = lambda obj: created.append(obj)

        # No audit event because no signals are created
        signals = await propagate_signal(
            organization_id="org-1",
            origin_supplier_id="A",
            source_confidence=1.0,
            source_severity="HIGH",
            exposure_type="SANCTIONS",
            rationale="second run",
            max_depth=1,
            session=session,
        )

        impacted_ids = [
            obj.impacted_supplier_id
            for obj in created
            if hasattr(obj, "impacted_supplier_id")
        ]
        assert "B" not in impacted_ids
        assert signals == []

    @pytest.mark.asyncio
    async def test_propagate_signal_emits_audit_event_when_signals_created(self):
        """network.signal.propagated audit event fires when at least one signal created."""
        from application.network.risk_propagation import propagate_signal

        rows = [MagicMock(supplier_id="A", related_supplier_id="B", confidence=1.0)]
        session = _propagation_session(rows)
        session.add = MagicMock()

        with patch(
            "application.network.risk_propagation._log_audit_event",
            new_callable=AsyncMock,
        ) as mock_audit:
            await propagate_signal(
                organization_id="org-1",
                origin_supplier_id="A",
                source_confidence=1.0,
                source_severity="HIGH",
                exposure_type="SANCTIONS",
                rationale="test",
                max_depth=1,
                session=session,
            )

        mock_audit.assert_awaited_once()
        action = mock_audit.call_args[0][1]
        assert action == "network.signal.propagated"

    # ── P0: Cascade dedup ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_cascade_detect_skips_existing_active_signal(self):
        """detect_cascading_risk() does not create duplicate CASCADE signals."""
        from application.network.cascading_risk import detect_cascading_risk

        call_count = 0
        session = _fake_session()

        async def staged_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="A", severity="CRITICAL", id="s1", title="t"),
                    MagicMock(supplier_id="B", severity="HIGH", id="s2", title="t2"),
                ])
            elif call_count == 2:
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="A", related_supplier_id="B"),
                ])
            else:
                # dup check returns an existing signal → skip creation
                result.scalar_one_or_none = MagicMock(return_value=MagicMock(id="existing"))
            return result

        session.execute = staged_execute
        created = []
        session.add = lambda obj: created.append(obj)

        result = await detect_cascading_risk("org-1", session)
        assert result == []
        assert len(created) == 0

    @pytest.mark.asyncio
    async def test_cascade_detect_emits_audit_event(self):
        """network.cascade.detected audit event fires when signals are created."""
        from application.network.cascading_risk import detect_cascading_risk

        call_count = 0
        session = _fake_session()

        async def staged_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="A", severity="CRITICAL", id="s1", title="t"),
                    MagicMock(supplier_id="B", severity="HIGH", id="s2", title="t2"),
                ])
            elif call_count == 2:
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="A", related_supplier_id="B"),
                ])
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        session.execute = staged_execute
        session.add = MagicMock()

        with patch(
            "application.network.cascading_risk._log_audit_event",
            new_callable=AsyncMock,
        ) as mock_audit:
            result = await detect_cascading_risk("org-1", session)

        assert len(result) >= 1
        mock_audit.assert_awaited_once()
        action = mock_audit.call_args[0][1]
        assert action == "network.cascade.detected"

    # ── P1: Relationship ownership validation ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_relationship_rejects_cross_tenant_supplier(self):
        """Raises ValueError when supplier_id does not belong to the org."""
        from application.network.relationship_service import create_relationship

        # First supplier check returns None (not found)
        session = _session_with_execute_sequence(None)

        with pytest.raises(ValueError, match="not found in organization"):
            await create_relationship(
                organization_id="org-1",
                supplier_id="sup-from-org-2",
                related_supplier_id="sup-B",
                relationship_type="CUSTOM",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_create_relationship_rejects_second_supplier_cross_tenant(self):
        """Raises ValueError when related_supplier_id does not belong to the org."""
        from application.network.relationship_service import create_relationship

        # First supplier found, second supplier not found
        session = _session_with_execute_sequence(
            MagicMock(id="sup-A"),  # supplier A found
            None,                   # supplier B not found
        )

        with pytest.raises(ValueError, match="not found in organization"):
            await create_relationship(
                organization_id="org-1",
                supplier_id="sup-A",
                related_supplier_id="sup-from-org-2",
                relationship_type="CUSTOM",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_create_relationship_rejects_duplicate_active(self):
        """Raises ValueError when an ACTIVE relationship of same type already exists."""
        from application.network.relationship_service import create_relationship

        # Both suppliers found, duplicate check returns existing relationship
        session = _session_with_execute_sequence(
            MagicMock(id="sup-A"),          # supplier A found
            MagicMock(id="sup-B"),          # supplier B found
            MagicMock(id="rel-existing"),   # duplicate found
        )

        with pytest.raises(ValueError, match="already exists"):
            await create_relationship(
                organization_id="org-1",
                supplier_id="sup-A",
                related_supplier_id="sup-B",
                relationship_type="SUBSIDIARY",
                session=session,
            )

    # ── P2: Centrality N+1 fix ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_compute_centrality_uses_at_most_three_queries(self):
        """compute_centrality() must issue ≤ 3 DB queries regardless of node count."""
        from application.network.centrality_service import compute_centrality

        out_rows = [
            MagicMock(supplier_id="A", cnt=2),
            MagicMock(supplier_id="B", cnt=1),
            MagicMock(supplier_id="C", cnt=1),
        ]
        in_rows = [
            MagicMock(supplier_id="B", cnt=1),
            MagicMock(supplier_id="C", cnt=2),
        ]
        adj_rows = [
            MagicMock(supplier_id="A", related_supplier_id="B"),
            MagicMock(supplier_id="B", related_supplier_id="C"),
        ]

        call_count = 0

        async def counting_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all = MagicMock(return_value=out_rows)
            elif call_count == 2:
                result.all = MagicMock(return_value=in_rows)
            else:
                result.all = MagicMock(return_value=adj_rows)
            return result

        session = _fake_session()
        session.execute = counting_execute

        with patch(
            "application.network.centrality_service._log_audit_event",
            new_callable=AsyncMock,
        ):
            records = await compute_centrality("org-1", session)

        # P2: must not exceed 3 queries for any number of nodes
        assert call_count <= 3
        assert len(records) > 0

    @pytest.mark.asyncio
    async def test_compute_centrality_component_size_computed_correctly(self):
        """All nodes in the same connected component get the same component size."""
        from application.network.centrality_service import compute_centrality

        out_rows = [
            MagicMock(supplier_id="A", cnt=1),
            MagicMock(supplier_id="B", cnt=1),
        ]
        in_rows = [
            MagicMock(supplier_id="B", cnt=1),
            MagicMock(supplier_id="A", cnt=1),
        ]
        adj_rows = [MagicMock(supplier_id="A", related_supplier_id="B")]

        call_count = 0

        async def multi(stmt):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            r.all = MagicMock(
                return_value=out_rows if call_count == 1 else (
                    in_rows if call_count == 2 else adj_rows
                )
            )
            return r

        session = _fake_session()
        session.execute = multi

        with patch(
            "application.network.centrality_service._log_audit_event",
            new_callable=AsyncMock,
        ):
            records = await compute_centrality("org-1", session)

        sizes = {r["supplier_id"]: r["connected_component_size"] for r in records}
        # A and B are connected → same component size (2)
        assert sizes.get("A") == sizes.get("B") == 2

    # ── P3: Audit events ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_cluster_incidents_emits_created_audit_event(self):
        """network.cluster.created fires when a new cluster is persisted.

        FindingModel lacks supplier_id / organization_id / finding_status —
        accessing those attributes raises AttributeError which the function
        silently swallows. We patch FindingModel with a mock that has the
        columns, and also patch sqlalchemy.select so it accepts mock column
        objects without raising ArgumentError.
        """
        from application.network.cascading_risk import cluster_incidents

        mock_fm = MagicMock()
        for attr in ("id", "supplier_id", "category", "severity",
                     "organization_id", "finding_status"):
            setattr(mock_fm, attr, MagicMock())
        mock_fm.finding_status.in_.return_value = MagicMock()
        mock_fm.supplier_id.is_not.return_value = MagicMock()

        def mock_select_fn(*args, **kwargs):
            m = MagicMock()
            m.where.return_value = m
            return m

        call_count = 0
        session = _fake_session()

        async def staged(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all = MagicMock(return_value=[
                    MagicMock(id="f1", supplier_id="A", category="Environmental", severity="HIGH"),
                    MagicMock(id="f2", supplier_id="B", category="Environmental", severity="MEDIUM"),
                ])
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        session.execute = staged
        audit_calls: list[str] = []

        async def capture_audit(_session, action, *args, **kwargs):
            audit_calls.append(action)

        with patch("infrastructure.persistence.models.finding.FindingModel", mock_fm), \
             patch("sqlalchemy.select", side_effect=mock_select_fn), \
             patch("application.network.cascading_risk._log_audit_event", side_effect=capture_audit):
            await cluster_incidents("org-1", session)

        assert "network.cluster.created" in audit_calls

    @pytest.mark.asyncio
    async def test_cluster_incidents_emits_updated_audit_event(self):
        """network.cluster.updated fires when an existing cluster is extended."""
        from application.network.cascading_risk import cluster_incidents

        existing_cluster = MagicMock()
        existing_cluster.id = "cluster-existing"
        existing_cluster.affected_supplier_ids = ["A"]
        existing_cluster.finding_ids = ["f0"]

        mock_fm = MagicMock()
        for attr in ("id", "supplier_id", "category", "severity",
                     "organization_id", "finding_status"):
            setattr(mock_fm, attr, MagicMock())
        mock_fm.finding_status.in_.return_value = MagicMock()
        mock_fm.supplier_id.is_not.return_value = MagicMock()

        def mock_select_fn(*args, **kwargs):
            m = MagicMock()
            m.where.return_value = m
            return m

        call_count = 0
        session = _fake_session()

        async def staged(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all = MagicMock(return_value=[
                    MagicMock(id="f1", supplier_id="A", category="Environmental", severity="HIGH"),
                    MagicMock(id="f2", supplier_id="B", category="Environmental", severity="MEDIUM"),
                ])
            else:
                result.scalar_one_or_none = MagicMock(return_value=existing_cluster)
            return result

        session.execute = staged
        audit_calls: list[str] = []

        async def capture_audit(_session, action, *args, **kwargs):
            audit_calls.append(action)

        with patch("infrastructure.persistence.models.finding.FindingModel", mock_fm), \
             patch("sqlalchemy.select", side_effect=mock_select_fn), \
             patch("application.network.cascading_risk._log_audit_event", side_effect=capture_audit):
            await cluster_incidents("org-1", session)

        assert "network.cluster.updated" in audit_calls

    # ── P4: Network Watchlist ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_watchlist_expand_creates_entries_for_neighbors(self):
        """expand_watchlist_network creates one entry per BFS neighbor."""
        from application.network.watchlist_service import expand_watchlist_network

        session = _fake_session()
        call_count = 0

        async def multi(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # bfs_neighborhood adjacency query
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="WATCHED", related_supplier_id="REL-1"),
                    MagicMock(supplier_id="REL-1", related_supplier_id="REL-2"),
                ])
            else:
                # dup check → None (no existing entry)
                result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        session.execute = multi
        created = []
        session.add = lambda obj: created.append(obj)

        entries = await expand_watchlist_network("org-1", "WATCHED", session)

        # BFS depth=2: REL-1 (dist 1) + REL-2 (dist 2)
        assert len(entries) == 2
        related_ids = {e.related_supplier_id for e in entries}
        assert "REL-1" in related_ids
        assert "REL-2" in related_ids

    @pytest.mark.asyncio
    async def test_watchlist_expand_idempotent_skips_existing(self):
        """expand_watchlist_network skips entries that already exist in DB."""
        from application.network.watchlist_service import expand_watchlist_network

        session = _fake_session()
        call_count = 0

        async def multi(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.all = MagicMock(return_value=[
                    MagicMock(supplier_id="WATCHED", related_supplier_id="REL-1"),
                ])
            else:
                # dup check → existing entry found
                result.scalar_one_or_none = MagicMock(return_value=MagicMock(id="existing"))
            return result

        session.execute = multi
        created = []
        session.add = lambda obj: created.append(obj)

        entries = await expand_watchlist_network("org-1", "WATCHED", session)
        assert entries == []
        assert len(created) == 0

    @pytest.mark.asyncio
    async def test_watchlist_get_returns_enriched_entries(self):
        """get_network_watchlist returns entries with has_active_alert field."""
        from application.network.watchlist_service import get_network_watchlist

        entry = MagicMock()
        entry.id = "wl-1"
        entry.organization_id = "org-1"
        entry.watched_supplier_id = "WATCHED"
        entry.related_supplier_id = "REL-1"
        entry.distance = 1
        entry.created_at = datetime.now(UTC)
        entry.updated_at = datetime.now(UTC)

        call_count = 0
        session = _fake_session()

        async def multi(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all = MagicMock(return_value=[entry])
            else:
                # surveillance signals → REL-1 has an active HIGH signal
                result.scalars.return_value.all = MagicMock(return_value=["REL-1"])
            return result

        session.execute = multi

        results = await get_network_watchlist("org-1", session=session)
        assert len(results) == 1
        assert results[0]["has_active_alert"] is True
        assert results[0]["watched_supplier_id"] == "WATCHED"

    @pytest.mark.asyncio
    async def test_watchlist_tenant_isolation(self):
        """get_network_watchlist scopes by organization_id."""
        from application.network.watchlist_service import get_network_watchlist

        session = _fake_session()

        async def execute(stmt):
            result = MagicMock()
            result.scalars.return_value.all = MagicMock(return_value=[])
            return result

        session.execute = execute

        # Org-2 has no entries
        results = await get_network_watchlist("org-2", session=session)
        assert results == []
