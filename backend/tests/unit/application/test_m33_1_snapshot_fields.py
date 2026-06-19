"""M33.1 — Snapshot Field Persistence Tests.

Verifies that CopilotMessage domain entity carries the three new audit
snapshot fields with correct defaults.
"""

from __future__ import annotations

from domain.copilot import CopilotMessage
from domain.enums import CopilotMessageRole, EntityStatus


class TestSnapshotFieldDefaults:
    def _make_msg(self, **kwargs) -> CopilotMessage:
        return CopilotMessage(
            conversation_id="conv-1",
            organization_id="org-1",
            user_id="user-1",
            role=CopilotMessageRole.USER,
            content="hello",
            status=EntityStatus.ACTIVE,
            **kwargs,
        )

    def test_retrieval_snapshot_default_is_empty_dict(self):
        msg = self._make_msg()
        assert msg.retrieval_snapshot == {}

    def test_assembled_context_default_is_empty_string(self):
        msg = self._make_msg()
        assert msg.assembled_context == ""

    def test_system_prompt_snapshot_default_is_empty_string(self):
        msg = self._make_msg()
        assert msg.system_prompt_snapshot == ""

    def test_retrieval_snapshot_can_be_set(self):
        snapshot = {"supplier_retriever": {"source_ids": ["s1"], "data": []}}
        msg = self._make_msg(retrieval_snapshot=snapshot)
        assert msg.retrieval_snapshot == snapshot
        assert msg.retrieval_snapshot["supplier_retriever"]["source_ids"] == ["s1"]

    def test_assembled_context_can_be_set(self):
        ctx = "[SUPPLIER_RETRIEVER] Top suppliers by risk\n[...]"
        msg = self._make_msg(assembled_context=ctx)
        assert msg.assembled_context == ctx

    def test_system_prompt_snapshot_can_be_set(self):
        prompt = "You are the EIOS AI Sustainability Copilot.\nCONTEXT DATA:\n..."
        msg = self._make_msg(system_prompt_snapshot=prompt)
        assert msg.system_prompt_snapshot == prompt

    def test_snapshot_fields_independent_per_instance(self):
        """Mutable default for retrieval_snapshot must not be shared."""
        msg1 = self._make_msg()
        msg2 = self._make_msg()
        msg1.retrieval_snapshot["key"] = "value"
        assert "key" not in msg2.retrieval_snapshot
