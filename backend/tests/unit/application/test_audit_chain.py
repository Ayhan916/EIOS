"""Unit tests for E3-F2 — Immutable Audit Log hash-chain (ADR-006).

The hash function must be:
- Deterministic (same inputs → same output)
- Sensitive to every field (changing any input changes the hash)
- Chainable (previous_hash binds entries together)
"""

import hashlib
import json

import pytest

from application.audit_chain import compute_entry_hash, verify_entry_hash


class TestComputeEntryHash:
    def _expected(
        self,
        event_id: str,
        action: str,
        actor_id: str | None,
        metadata: dict,
        previous_hash: str,
    ) -> str:
        payload = json.dumps(metadata, sort_keys=True, ensure_ascii=True)
        raw = f"{event_id}|{action}|{actor_id or ''}|{payload}|{previous_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def test_returns_64_char_hex_string(self) -> None:
        h = compute_entry_hash("id1", "action.test", None, {}, "")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self) -> None:
        h1 = compute_entry_hash("id1", "test.action", "actor-1", {"k": "v"}, "prev")
        h2 = compute_entry_hash("id1", "test.action", "actor-1", {"k": "v"}, "prev")
        assert h1 == h2

    def test_genesis_entry_uses_empty_previous(self) -> None:
        h = compute_entry_hash("id1", "action", None, {}, "")
        expected = self._expected("id1", "action", None, {}, "")
        assert h == expected

    def test_sensitive_to_event_id(self) -> None:
        h1 = compute_entry_hash("id-A", "act", None, {}, "")
        h2 = compute_entry_hash("id-B", "act", None, {}, "")
        assert h1 != h2

    def test_sensitive_to_action(self) -> None:
        h1 = compute_entry_hash("id1", "assessment.created", None, {}, "")
        h2 = compute_entry_hash("id1", "assessment.approved", None, {}, "")
        assert h1 != h2

    def test_sensitive_to_actor_id(self) -> None:
        h1 = compute_entry_hash("id1", "act", "user-1", {}, "")
        h2 = compute_entry_hash("id1", "act", "user-2", {}, "")
        assert h1 != h2

    def test_sensitive_to_metadata(self) -> None:
        h1 = compute_entry_hash("id1", "act", None, {"key": "value-A"}, "")
        h2 = compute_entry_hash("id1", "act", None, {"key": "value-B"}, "")
        assert h1 != h2

    def test_sensitive_to_previous_hash(self) -> None:
        h1 = compute_entry_hash("id1", "act", None, {}, "prev-hash-A")
        h2 = compute_entry_hash("id1", "act", None, {}, "prev-hash-B")
        assert h1 != h2

    def test_none_actor_treated_as_empty_string(self) -> None:
        h_none = compute_entry_hash("id1", "act", None, {}, "")
        h_empty = compute_entry_hash("id1", "act", "", {}, "")
        assert h_none == h_empty

    def test_metadata_keys_sorted_for_determinism(self) -> None:
        h1 = compute_entry_hash("id1", "act", None, {"b": 2, "a": 1}, "")
        h2 = compute_entry_hash("id1", "act", None, {"a": 1, "b": 2}, "")
        assert h1 == h2


class TestChainBinding:
    """Verify that chaining entries produces distinct, order-sensitive hashes."""

    def test_chain_of_three(self) -> None:
        h1 = compute_entry_hash("e1", "act1", None, {}, "")
        h2 = compute_entry_hash("e2", "act2", None, {}, h1)
        h3 = compute_entry_hash("e3", "act3", None, {}, h2)

        assert h1 != h2 != h3
        assert len({h1, h2, h3}) == 3

    def test_reordering_breaks_chain(self) -> None:
        h1 = compute_entry_hash("e1", "act", None, {}, "")
        h2_correct = compute_entry_hash("e2", "act", None, {}, h1)
        h2_wrong = compute_entry_hash("e2", "act", None, {}, "")  # chain broken
        assert h2_correct != h2_wrong


class TestVerifyEntryHash:
    def test_valid_hash_returns_true(self) -> None:
        stored = compute_entry_hash("id1", "act", "user", {"x": 1}, "prev")
        assert verify_entry_hash("id1", "act", "user", {"x": 1}, "prev", stored) is True

    def test_tampered_action_returns_false(self) -> None:
        stored = compute_entry_hash("id1", "original.act", None, {}, "")
        assert verify_entry_hash("id1", "tampered.act", None, {}, "", stored) is False

    def test_tampered_metadata_returns_false(self) -> None:
        stored = compute_entry_hash("id1", "act", None, {"amount": 100}, "")
        assert verify_entry_hash("id1", "act", None, {"amount": 999}, "", stored) is False

    def test_wrong_previous_hash_returns_false(self) -> None:
        stored = compute_entry_hash("id1", "act", None, {}, "real-prev")
        assert verify_entry_hash("id1", "act", None, {}, "injected-prev", stored) is False
