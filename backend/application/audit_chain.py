"""SHA-256 hash-chain computation for the Immutable Audit Log (ADR-006).

Each audit entry's hash covers:
  event_id | action | actor_id | payload (JSON, sorted keys) | previous_hash

The "|" separator is a literal pipe character used as a field delimiter to
prevent accidental collisions between concatenated values.

The previous_hash is "" for the genesis entry (no prior event in the chain).
"""

import hashlib
import json
from typing import Any


def compute_entry_hash(
    event_id: str,
    action: str,
    actor_id: str | None,
    event_metadata: dict[str, Any],
    previous_hash: str,
) -> str:
    """Return the SHA-256 hex digest that binds this entry to the chain.

    All inputs are normalised to UTF-8 strings before hashing.
    event_metadata is serialised with sorted keys for determinism.
    """
    payload = json.dumps(event_metadata, sort_keys=True, ensure_ascii=True)
    raw = f"{event_id}|{action}|{actor_id or ''}|{payload}|{previous_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_entry_hash(
    event_id: str,
    action: str,
    actor_id: str | None,
    event_metadata: dict[str, Any],
    previous_hash: str,
    stored_hash: str,
) -> bool:
    """Return True if the stored hash matches the recomputed value."""
    return compute_entry_hash(event_id, action, actor_id, event_metadata, previous_hash) == stored_hash
