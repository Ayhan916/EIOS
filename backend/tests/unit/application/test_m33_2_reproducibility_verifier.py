"""M33.2 — Historical Reproducibility Verifier Tests.

All tests use mocked repositories to avoid DB dependencies.
Verifies hash integrity, answer integrity, prompt integrity,
snapshot integrity, and tenant isolation.

Note: verify_audit_package() lazy-imports repos inside the function body,
so we patch at the infrastructure module path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Pre-import to ensure copilot_audit repo module is in sys.modules before patching
from application.copilot.audit_package_service import compute_package_hash
from application.copilot.reproducibility_verifier import (
    VerificationCheck,
    VerificationResult,
    verify_audit_package,
)

_PKG_REPO_PATH = (
    "infrastructure.persistence.repositories.copilot_audit.SQLCopilotAuditPackageRepository"
)
_MSG_REPO_PATH = "infrastructure.persistence.repositories.copilot.SQLCopilotMessageRepository"


def _make_payload(answer: str = "Test answer", prompt: str = "System prompt") -> dict:
    return {
        "schema_version": "1.0",
        "message_id": "msg-1",
        "answer": answer,
        "system_prompt_snapshot": prompt,
        "retrieval_snapshot": {"supplier_retriever": {"source_ids": ["s1"]}},
        "citations": [],
        "confidence_level": "High",
    }


def _make_pkg(org_id: str = "org-1", payload: dict | None = None) -> MagicMock:
    payload = payload or _make_payload()
    pkg = MagicMock()
    pkg.id = "pkg-1"
    pkg.message_id = "msg-1"
    pkg.organization_id = org_id
    pkg.json_payload = payload
    pkg.package_hash = compute_package_hash(payload)
    return pkg


def _make_msg(
    content: str = "Test answer",
    system_prompt: str = "System prompt",
    retrieval_snapshot: dict | None = None,
) -> MagicMock:
    msg = MagicMock()
    msg.id = "msg-1"
    msg.content = content
    msg.system_prompt_snapshot = system_prompt
    msg.retrieval_snapshot = retrieval_snapshot or {"supplier_retriever": {"source_ids": ["s1"]}}
    return msg


class TestHashIntegrity:
    @pytest.mark.asyncio
    async def test_valid_package_passes_hash_check(self):
        pkg = _make_pkg()
        msg = _make_msg()
        session = AsyncMock()

        with (
            patch(_PKG_REPO_PATH) as MockPkgRepo,
            patch(_MSG_REPO_PATH) as MockMsgRepo,
        ):
            MockPkgRepo.return_value.get_by_id = AsyncMock(return_value=pkg)
            MockMsgRepo.return_value.get_by_id = AsyncMock(return_value=msg)
            result = await verify_audit_package("pkg-1", "org-1", session)

        hash_check = next(c for c in result.checks if c.name == "hash_integrity")
        assert hash_check.passed is True
        assert result.overall == "PASS"

    @pytest.mark.asyncio
    async def test_tampered_payload_fails_hash_check(self):
        payload = _make_payload()
        original_hash = compute_package_hash(payload)
        payload["answer"] = "TAMPERED"  # Mutate after hashing

        pkg = MagicMock()
        pkg.id = "pkg-1"
        pkg.message_id = "msg-1"
        pkg.organization_id = "org-1"
        pkg.json_payload = payload
        pkg.package_hash = original_hash  # Stored hash is for original payload

        msg = _make_msg(content="TAMPERED")
        session = AsyncMock()

        with (
            patch(_PKG_REPO_PATH) as MockPkgRepo,
            patch(_MSG_REPO_PATH) as MockMsgRepo,
        ):
            MockPkgRepo.return_value.get_by_id = AsyncMock(return_value=pkg)
            MockMsgRepo.return_value.get_by_id = AsyncMock(return_value=msg)
            result = await verify_audit_package("pkg-1", "org-1", session)

        hash_check = next(c for c in result.checks if c.name == "hash_integrity")
        assert hash_check.passed is False
        assert result.overall == "FAIL"


class TestAnswerIntegrity:
    @pytest.mark.asyncio
    async def test_answer_matches_passes(self):
        pkg = _make_pkg()
        msg = _make_msg(content="Test answer")
        session = AsyncMock()

        with (
            patch(_PKG_REPO_PATH) as MockPkgRepo,
            patch(_MSG_REPO_PATH) as MockMsgRepo,
        ):
            MockPkgRepo.return_value.get_by_id = AsyncMock(return_value=pkg)
            MockMsgRepo.return_value.get_by_id = AsyncMock(return_value=msg)
            result = await verify_audit_package("pkg-1", "org-1", session)

        answer_check = next(c for c in result.checks if c.name == "answer_integrity")
        assert answer_check.passed is True

    @pytest.mark.asyncio
    async def test_answer_mismatch_fails(self):
        pkg = _make_pkg()
        msg = _make_msg(content="Different content from what is in payload")
        session = AsyncMock()

        with (
            patch(_PKG_REPO_PATH) as MockPkgRepo,
            patch(_MSG_REPO_PATH) as MockMsgRepo,
        ):
            MockPkgRepo.return_value.get_by_id = AsyncMock(return_value=pkg)
            MockMsgRepo.return_value.get_by_id = AsyncMock(return_value=msg)
            result = await verify_audit_package("pkg-1", "org-1", session)

        answer_check = next(c for c in result.checks if c.name == "answer_integrity")
        assert answer_check.passed is False
        assert result.overall == "FAIL"


class TestPromptIntegrity:
    @pytest.mark.asyncio
    async def test_prompt_mismatch_fails(self):
        pkg = _make_pkg(payload=_make_payload(prompt="Original system prompt"))
        msg = _make_msg(system_prompt="Modified system prompt")
        session = AsyncMock()

        with (
            patch(_PKG_REPO_PATH) as MockPkgRepo,
            patch(_MSG_REPO_PATH) as MockMsgRepo,
        ):
            MockPkgRepo.return_value.get_by_id = AsyncMock(return_value=pkg)
            MockMsgRepo.return_value.get_by_id = AsyncMock(return_value=msg)
            result = await verify_audit_package("pkg-1", "org-1", session)

        prompt_check = next(c for c in result.checks if c.name == "prompt_integrity")
        assert prompt_check.passed is False


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_wrong_org_fails_tenant_check(self):
        pkg = _make_pkg(org_id="org-other")
        session = AsyncMock()

        with patch(_PKG_REPO_PATH) as MockPkgRepo:
            MockPkgRepo.return_value.get_by_id = AsyncMock(return_value=pkg)
            result = await verify_audit_package("pkg-1", "org-requester", session)

        assert result.overall == "FAIL"
        tenant_check = next(c for c in result.checks if c.name == "tenant_check")
        assert tenant_check.passed is False

    @pytest.mark.asyncio
    async def test_correct_org_passes_tenant_check(self):
        pkg = _make_pkg(org_id="org-1")
        msg = _make_msg()
        session = AsyncMock()

        with (
            patch(_PKG_REPO_PATH) as MockPkgRepo,
            patch(_MSG_REPO_PATH) as MockMsgRepo,
        ):
            MockPkgRepo.return_value.get_by_id = AsyncMock(return_value=pkg)
            MockMsgRepo.return_value.get_by_id = AsyncMock(return_value=msg)
            result = await verify_audit_package("pkg-1", "org-1", session)

        # No tenant_check failure should exist for correct org
        tenant_failures = [c for c in result.checks if c.name == "tenant_check" and not c.passed]
        assert tenant_failures == []


class TestPackageNotFound:
    @pytest.mark.asyncio
    async def test_missing_package_returns_fail(self):
        session = AsyncMock()

        with patch(_PKG_REPO_PATH) as MockPkgRepo:
            MockPkgRepo.return_value.get_by_id = AsyncMock(return_value=None)
            result = await verify_audit_package("missing-pkg", "org-1", session)

        assert result.overall == "FAIL"
        assert any(not c.passed for c in result.checks)


class TestVerificationResult:
    def test_passed_property_true_on_pass(self):
        result = VerificationResult(
            package_id="p1",
            message_id="m1",
            organization_id="o1",
            overall="PASS",
        )
        assert result.passed is True

    def test_passed_property_false_on_fail(self):
        result = VerificationResult(
            package_id="p1",
            message_id="m1",
            organization_id="o1",
            overall="FAIL",
        )
        assert result.passed is False

    def test_verification_check_structure(self):
        check = VerificationCheck(name="hash_integrity", passed=True, detail="Hash matches")
        assert check.name == "hash_integrity"
        assert check.passed is True
        assert check.detail == "Hash matches"
