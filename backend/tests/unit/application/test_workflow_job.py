"""Unit tests for WorkflowJob domain and async executor logic (M12)."""

from __future__ import annotations

from datetime import UTC, datetime

from domain.workflow_job import WorkflowJob


class TestWorkflowJobDomain:
    def test_default_status_is_pending(self) -> None:
        job = WorkflowJob(workflow_type="quick_scan", query="Test query")
        assert job.job_status == "pending"

    def test_id_is_auto_generated_uuid(self) -> None:
        job = WorkflowJob(workflow_type="quick_scan", query="Test query")
        assert job.id
        assert len(job.id) == 36  # UUID4 format

    def test_two_jobs_have_different_ids(self) -> None:
        job1 = WorkflowJob(workflow_type="quick_scan", query="q")
        job2 = WorkflowJob(workflow_type="quick_scan", query="q")
        assert job1.id != job2.id

    def test_created_at_is_set(self) -> None:
        job = WorkflowJob(workflow_type="quick_scan", query="q")
        assert isinstance(job.created_at, datetime)

    def test_optional_fields_default_to_none(self) -> None:
        job = WorkflowJob(workflow_type="quick_scan", query="q")
        assert job.workflow_run_id is None
        assert job.error is None
        assert job.started_at is None
        assert job.completed_at is None
        assert job.created_by is None

    def test_job_metadata_defaults_to_empty_dict(self) -> None:
        job = WorkflowJob(workflow_type="quick_scan", query="q")
        assert job.job_metadata == {}

    def test_workflow_type_stored(self) -> None:
        job = WorkflowJob(workflow_type="due_diligence", query="Assess ACME Corp")
        assert job.workflow_type == "due_diligence"

    def test_query_stored(self) -> None:
        job = WorkflowJob(workflow_type="quick_scan", query="Assess ACME ESG performance")
        assert job.query == "Assess ACME ESG performance"

    def test_created_by_stored(self) -> None:
        job = WorkflowJob(workflow_type="quick_scan", query="q", created_by="user-123")
        assert job.created_by == "user-123"

    def test_job_metadata_stored(self) -> None:
        meta = {"sector": "manufacturing", "priority": "high"}
        job = WorkflowJob(workflow_type="quick_scan", query="q", job_metadata=meta)
        assert job.job_metadata == meta

    def test_status_can_be_overridden(self) -> None:
        job = WorkflowJob(workflow_type="quick_scan", query="q", job_status="running")
        assert job.job_status == "running"

    def test_valid_statuses(self) -> None:
        for s in ("pending", "running", "completed", "failed"):
            job = WorkflowJob(workflow_type="quick_scan", query="q", job_status=s)
            assert job.job_status == s

    def test_workflow_run_id_linkage(self) -> None:
        job = WorkflowJob(
            workflow_type="quick_scan",
            query="q",
            workflow_run_id="run-abc-123",
            job_status="completed",
        )
        assert job.workflow_run_id == "run-abc-123"

    def test_error_stored_on_failed_job(self) -> None:
        job = WorkflowJob(
            workflow_type="quick_scan",
            query="q",
            job_status="failed",
            error="LLM provider unavailable",
        )
        assert job.error == "LLM provider unavailable"

    def test_timestamps_on_completed_job(self) -> None:
        now = datetime.now(UTC)
        job = WorkflowJob(
            workflow_type="quick_scan",
            query="q",
            job_status="completed",
            started_at=now,
            completed_at=now,
        )
        assert job.started_at == now
        assert job.completed_at == now


class TestWorkflowJobLifecycle:
    """Validate state transition semantics."""

    def _pending(self) -> WorkflowJob:
        return WorkflowJob(
            workflow_type="quick_scan",
            query="Assess ACME Corp ESG performance",
            created_by="user-001",
        )

    def test_transition_pending_to_running(self) -> None:
        job = self._pending()
        assert job.job_status == "pending"
        job.job_status = "running"
        job.started_at = datetime.now(UTC)
        assert job.job_status == "running"
        assert job.started_at is not None

    def test_transition_running_to_completed(self) -> None:
        job = self._pending()
        job.job_status = "running"
        job.started_at = datetime.now(UTC)
        job.job_status = "completed"
        job.workflow_run_id = "run-xyz"
        job.completed_at = datetime.now(UTC)
        assert job.job_status == "completed"
        assert job.workflow_run_id == "run-xyz"
        assert job.completed_at is not None

    def test_transition_running_to_failed(self) -> None:
        job = self._pending()
        job.job_status = "running"
        job.job_status = "failed"
        job.error = "Network timeout during LLM call"
        job.completed_at = datetime.now(UTC)
        assert job.job_status == "failed"
        assert job.error
        assert job.workflow_run_id is None  # not set on failure

    def test_failed_job_has_no_workflow_run_id(self) -> None:
        job = self._pending()
        job.job_status = "failed"
        job.error = "Internal error"
        assert job.workflow_run_id is None

    def test_completed_job_has_no_error(self) -> None:
        job = self._pending()
        job.job_status = "completed"
        job.workflow_run_id = "run-abc"
        # error should remain None for a clean completion
        assert job.error is None
