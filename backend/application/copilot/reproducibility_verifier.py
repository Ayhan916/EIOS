"""Historical Reproducibility Verifier — M33.2.

Given a stored CopilotAuditPackage, verifies:
  1. The stored package_hash matches the recomputed hash of json_payload
  2. The answer in json_payload matches the stored CopilotMessage.content
  3. The system_prompt_snapshot matches what was stored on the message

Returns a VerificationResult with PASS/FAIL status and per-check details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from .audit_package_service import compute_package_hash

logger = structlog.get_logger(__name__)


@dataclass
class VerificationCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class VerificationResult:
    package_id: str
    message_id: str
    organization_id: str
    overall: str  # "PASS" or "FAIL"
    checks: list[VerificationCheck] = field(default_factory=list)
    verified_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def passed(self) -> bool:
        return self.overall == "PASS"


async def verify_audit_package(
    package_id: str,
    org_id: str,
    session,
) -> VerificationResult:
    """Load a stored audit package and verify its integrity."""
    from infrastructure.persistence.repositories.copilot_audit import (
        SQLCopilotAuditPackageRepository,
        SQLCopilotMessageRepository,
    )

    pkg_repo = SQLCopilotAuditPackageRepository(session)
    msg_repo = SQLCopilotMessageRepository(session)

    pkg = await pkg_repo.get_by_id(package_id)
    checks: list[VerificationCheck] = []

    if pkg is None:
        return VerificationResult(
            package_id=package_id,
            message_id="",
            organization_id=org_id,
            overall="FAIL",
            checks=[VerificationCheck("package_exists", False, "Audit package not found")],
        )

    # Tenant isolation — never expose another org's package
    if pkg.organization_id != org_id:
        return VerificationResult(
            package_id=package_id,
            message_id="",
            organization_id=org_id,
            overall="FAIL",
            checks=[VerificationCheck("tenant_check", False, "Package does not belong to this organisation")],
        )

    # Check 1: Hash integrity
    recomputed = compute_package_hash(pkg.json_payload)
    hash_ok = recomputed == pkg.package_hash
    checks.append(VerificationCheck(
        "hash_integrity",
        hash_ok,
        "Hash matches" if hash_ok else f"Hash mismatch: stored={pkg.package_hash[:16]}… recomputed={recomputed[:16]}…",
    ))

    # Check 2: Message content matches answer in package
    msg = await msg_repo.get_by_id(pkg.message_id)
    if msg is None:
        checks.append(VerificationCheck("message_exists", False, "Original message not found in database"))
    else:
        stored_answer = pkg.json_payload.get("answer", "")
        answer_ok = msg.content == stored_answer
        checks.append(VerificationCheck(
            "answer_integrity",
            answer_ok,
            "Answer matches" if answer_ok else "Answer in package differs from stored message content",
        ))

        # Check 3: System prompt snapshot
        stored_prompt = pkg.json_payload.get("system_prompt_snapshot", "")
        prompt_ok = msg.system_prompt_snapshot == stored_prompt
        checks.append(VerificationCheck(
            "prompt_integrity",
            prompt_ok,
            "Prompt snapshot matches" if prompt_ok else "System prompt snapshot has diverged",
        ))

        # Check 4: Retrieval snapshot keys
        pkg_retrievers = set(pkg.json_payload.get("retrieval_snapshot", {}).keys())
        msg_retrievers = set(msg.retrieval_snapshot.keys())
        snapshot_ok = pkg_retrievers == msg_retrievers
        checks.append(VerificationCheck(
            "snapshot_integrity",
            snapshot_ok,
            "Retrieval snapshot keys match" if snapshot_ok else
            f"Snapshot key mismatch: package={sorted(pkg_retrievers)} message={sorted(msg_retrievers)}",
        ))

    overall = "PASS" if all(c.passed for c in checks) else "FAIL"

    logger.info(
        "audit_package_verified",
        package_id=package_id,
        overall=overall,
        checks_passed=sum(c.passed for c in checks),
        checks_total=len(checks),
    )

    return VerificationResult(
        package_id=package_id,
        message_id=pkg.message_id,
        organization_id=org_id,
        overall=overall,
        checks=checks,
    )
