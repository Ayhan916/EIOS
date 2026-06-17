"""Unit tests for the workflow engine, definitions, registry, and verdict extraction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.ports.llm import LLMResponse
from application.workflows.base import StepResult, WorkflowDefinition, WorkflowStep, extract_verdict
from application.workflows.definitions import (
    DUE_DILIGENCE,
    EVIDENCE_ANALYSIS,
    GOVERNANCE_REVIEW,
    QUICK_SCAN,
)
from application.workflows.engine import WorkflowEngine
from application.workflows.registry import WORKFLOW_TYPES, get_workflow_definition
from domain.enums import EntityStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_provider(content: str = "mock agent response") -> MagicMock:
    resp = LLMResponse(
        content=content,
        model="mock-model",
        provider="mock",
        input_tokens=10,
        output_tokens=20,
        stop_reason="end_turn",
    )
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=resp)
    provider.model_name = MagicMock(return_value="mock-model")
    provider.provider_name = MagicMock(return_value="mock")
    return provider


def make_mock_knowledge(chunks: list[str] | None = None) -> MagicMock:
    ks = MagicMock()
    ks.search = AsyncMock(return_value=chunks or [])
    return ks


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestWorkflowRegistry:
    def test_all_types_registered(self) -> None:
        assert set(WORKFLOW_TYPES) == {
            "due_diligence",
            "quick_scan",
            "evidence_analysis",
            "governance_review",
        }

    def test_get_due_diligence_definition(self) -> None:
        defn = get_workflow_definition("due_diligence")
        assert defn.workflow_type == "due_diligence"
        assert len(defn.steps) == 8

    def test_get_quick_scan_definition(self) -> None:
        defn = get_workflow_definition("quick_scan")
        assert len(defn.steps) == 4

    def test_get_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown workflow type"):
            get_workflow_definition("nonexistent")


# ---------------------------------------------------------------------------
# WorkflowDefinitions
# ---------------------------------------------------------------------------


class TestWorkflowDefinitions:
    def test_due_diligence_agent_sequence(self) -> None:
        types = [s.agent_type for s in DUE_DILIGENCE.steps]
        assert types[0] == "research"
        assert types[-1] == "reporting"
        assert "evaluation" in types

    def test_quick_scan_has_retrieval_step(self) -> None:
        retrieval_steps = [s for s in QUICK_SCAN.steps if s.retrieve_knowledge]
        assert len(retrieval_steps) == 1
        assert retrieval_steps[0].agent_type == "retrieval"

    def test_evidence_analysis_has_retrieval_step(self) -> None:
        retrieval_steps = [s for s in EVIDENCE_ANALYSIS.steps if s.retrieve_knowledge]
        assert len(retrieval_steps) >= 1

    def test_governance_review_contains_governance_agent(self) -> None:
        types = [s.agent_type for s in GOVERNANCE_REVIEW.steps]
        assert "governance" in types


# ---------------------------------------------------------------------------
# Verdict extraction
# ---------------------------------------------------------------------------


class TestExtractVerdict:
    def _make_step(self, agent_type: str, content: str) -> StepResult:
        return StepResult(agent_type=agent_type, step_index=0, content=content)

    def test_evaluation_approved_maps_to_pass(self) -> None:
        steps = [self._make_step("evaluation", "**Verdict:** Approved\nScore: 0.85")]
        verdict, _ = extract_verdict(steps)
        assert verdict == "pass"

    def test_evaluation_needs_revision_maps_to_conditional_pass(self) -> None:
        steps = [self._make_step("evaluation", "**Verdict:** Needs revision\nScore: 0.62")]
        verdict, _ = extract_verdict(steps)
        assert verdict == "conditional_pass"

    def test_evaluation_rejected_maps_to_fail(self) -> None:
        steps = [self._make_step("evaluation", "**Verdict:** Rejected\nMajor gaps identified.")]
        verdict, _ = extract_verdict(steps)
        assert verdict == "fail"

    def test_risk_level_extracted_from_esg_assessment(self) -> None:
        content = "### Overall Risk Level\nCritical — significant violations found."
        steps = [self._make_step("esg_assessment", content)]
        _, risk_level = extract_verdict(steps)
        assert risk_level == "Critical"

    def test_risk_level_extracted_inline_format(self) -> None:
        content = "**Overall Risk Level:** High\n\nJustification follows."
        steps = [self._make_step("esg_assessment", content)]
        _, risk_level = extract_verdict(steps)
        assert risk_level == "High"

    def test_critical_risk_without_evaluation_yields_fail(self) -> None:
        content = "### Overall Risk Level\nCritical — child labour confirmed."
        steps = [self._make_step("esg_assessment", content)]
        verdict, _ = extract_verdict(steps)
        assert verdict == "fail"

    def test_high_risk_without_evaluation_yields_conditional_pass(self) -> None:
        content = "### Overall Risk Level\nHigh — systemic governance gaps."
        steps = [self._make_step("esg_assessment", content)]
        verdict, _ = extract_verdict(steps)
        assert verdict == "conditional_pass"

    def test_low_risk_without_evaluation_yields_pass(self) -> None:
        content = "### Overall Risk Level\nLow — minor issues identified."
        steps = [self._make_step("esg_assessment", content)]
        verdict, _ = extract_verdict(steps)
        assert verdict == "pass"

    def test_empty_steps_yields_insufficient_evidence(self) -> None:
        verdict, risk_level = extract_verdict([])
        assert verdict == "insufficient_evidence"
        assert risk_level == "Unknown"

    def test_all_steps_errored_yields_insufficient_evidence(self) -> None:
        steps = [StepResult("research", 0, "", error="LLM call failed")]
        verdict, risk_level = extract_verdict(steps)
        assert verdict == "insufficient_evidence"
        assert risk_level == "Unknown"

    def test_critical_risk_promotes_pass_verdict_to_conditional(self) -> None:
        esg = self._make_step("esg_assessment", "**Overall Risk Level:** Critical — violations.")
        eval_step = self._make_step("evaluation", "**Verdict:** Approved\n")
        verdict, risk_level = extract_verdict([esg, eval_step])
        # Critical overrides "Approved" → promoted to conditional_pass
        assert verdict == "conditional_pass"
        assert risk_level == "Critical"


# ---------------------------------------------------------------------------
# WorkflowEngine
# ---------------------------------------------------------------------------


class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_engine_runs_all_steps(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[
                WorkflowStep("research"),
                WorkflowStep("reasoning"),
            ],
        )
        provider = make_mock_provider("response content")
        engine = WorkflowEngine(llm_provider=provider)
        workflow_run, agent_runs = await engine.run(defn, "test query", {})
        assert len(agent_runs) == 2
        assert workflow_run.steps_completed == 2

    @pytest.mark.asyncio
    async def test_engine_links_agent_runs_to_workflow(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[WorkflowStep("research"), WorkflowStep("reasoning")],
        )
        engine = WorkflowEngine(llm_provider=make_mock_provider())
        workflow_run, agent_runs = await engine.run(defn, "query", {})
        for ar in agent_runs:
            assert ar.workflow_run_id == workflow_run.id

    @pytest.mark.asyncio
    async def test_engine_step_indices_are_sequential(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[WorkflowStep("research"), WorkflowStep("reasoning"), WorkflowStep("reporting")],
        )
        engine = WorkflowEngine(llm_provider=make_mock_provider())
        _, agent_runs = await engine.run(defn, "query", {})
        indices = [ar.step_index for ar in agent_runs]
        assert indices == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_engine_calls_knowledge_search_for_retrieval_steps(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[
                WorkflowStep("research", retrieve_knowledge=False),
                WorkflowStep("retrieval", retrieve_knowledge=True, knowledge_limit=5),
            ],
        )
        knowledge = make_mock_knowledge(["chunk A", "chunk B"])
        engine = WorkflowEngine(llm_provider=make_mock_provider(), knowledge_search=knowledge)
        await engine.run(defn, "query", {})
        knowledge.search.assert_awaited_once_with("query", limit=5)

    @pytest.mark.asyncio
    async def test_engine_passes_prior_outputs_between_steps(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[
                WorkflowStep("research", pass_prior_outputs=True),
                WorkflowStep("reasoning", pass_prior_outputs=True),
            ],
        )
        provider = make_mock_provider("step output")
        engine = WorkflowEngine(llm_provider=provider)
        await engine.run(defn, "query", {})
        # Second call should contain "step output" in the messages passed to provider
        calls = provider.complete.call_args_list
        assert len(calls) == 2
        second_messages = calls[1][0][0]
        assert "step output" in second_messages[0].content

    @pytest.mark.asyncio
    async def test_engine_continues_after_step_failure(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[WorkflowStep("research"), WorkflowStep("reasoning")],
        )
        provider = make_mock_provider()
        provider.complete = AsyncMock(
            side_effect=[
                RuntimeError("API error"),
                LLMResponse(
                    content="ok",
                    model="m",
                    provider="p",
                    input_tokens=1,
                    output_tokens=1,
                    stop_reason="end_turn",
                ),
            ]
        )
        engine = WorkflowEngine(llm_provider=provider)
        workflow_run, agent_runs = await engine.run(defn, "query", {})
        assert agent_runs[0].error is not None
        assert agent_runs[1].error is None
        assert workflow_run.steps_completed == 2

    @pytest.mark.asyncio
    async def test_engine_marks_workflow_suspended_when_all_steps_fail(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[WorkflowStep("research")],
        )
        provider = make_mock_provider()
        provider.complete = AsyncMock(side_effect=RuntimeError("fatal"))
        engine = WorkflowEngine(llm_provider=provider)
        workflow_run, _ = await engine.run(defn, "query", {})
        assert workflow_run.status == EntityStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_engine_aggregates_token_usage(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[WorkflowStep("research"), WorkflowStep("reasoning")],
        )
        engine = WorkflowEngine(llm_provider=make_mock_provider())
        workflow_run, _ = await engine.run(defn, "query", {})
        assert workflow_run.total_input_tokens == 20  # 10 * 2 steps
        assert workflow_run.total_output_tokens == 40  # 20 * 2 steps

    @pytest.mark.asyncio
    async def test_engine_sets_verdict_and_risk_level(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[WorkflowStep("esg_assessment")],
        )
        provider = make_mock_provider(
            "### Overall Risk Level\nHigh — supply chain violations found."
        )
        engine = WorkflowEngine(llm_provider=provider)
        workflow_run, _ = await engine.run(defn, "query", {})
        assert workflow_run.overall_risk_level == "High"
        assert workflow_run.verdict == "conditional_pass"

    @pytest.mark.asyncio
    async def test_engine_without_knowledge_search_skips_retrieval(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[WorkflowStep("retrieval", retrieve_knowledge=True)],
        )
        provider = make_mock_provider()
        engine = WorkflowEngine(llm_provider=provider, knowledge_search=None)
        # Should not raise even without knowledge search
        workflow_run, agent_runs = await engine.run(defn, "query", {})
        assert len(agent_runs) == 1

    @pytest.mark.asyncio
    async def test_engine_metadata_passed_to_agents(self) -> None:
        defn = WorkflowDefinition(
            workflow_type="test_workflow",
            description="test",
            steps=[WorkflowStep("esg_assessment")],
        )
        provider = make_mock_provider()
        engine = WorkflowEngine(llm_provider=provider)
        await engine.run(defn, "query", {"nace_code": "C13", "entity_name": "Acme"})
        call_args = provider.complete.call_args
        messages = call_args[0][0]
        assert "C13" in messages[0].content
