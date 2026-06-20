"""Secret provider abstraction for M40.1 SSO hardening.

Design:
  - SecretProvider is the abstract interface.
  - InMemorySecretProvider is used in tests.
  - EnvironmentSecretProvider is the default: secrets are pre-loaded into
    environment variables by the operator (via Kubernetes Secrets, Vault
    Agent Injector, AWS Secrets Manager sidecar, etc.).
  - A future KMSSecretProvider can be added without touching callers.

The SecretReference ORM row stores (provider_name, identifier) only.
The raw secret value is never persisted to the database.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class SecretProvider(ABC):
    """Abstract interface for secret storage and retrieval."""

    @abstractmethod
    def store(self, identifier: str, value: str) -> str:
        """Store a secret value and return the identifier used to retrieve it."""

    @abstractmethod
    def retrieve(self, identifier: str) -> str | None:
        """Return the secret value for the given identifier, or None if absent."""

    @abstractmethod
    def delete(self, identifier: str) -> None:
        """Remove a secret. Silently a no-op if identifier does not exist."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short stable name stored in SecretReference.provider."""


class InMemorySecretProvider(SecretProvider):
    """Thread-unsafe in-process store — for tests only.

    Values are lost when the process exits. Never use in production.
    """

    provider_name = "in_memory"

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def store(self, identifier: str, value: str) -> str:
        self._store[identifier] = value
        return identifier

    def retrieve(self, identifier: str) -> str | None:
        return self._store.get(identifier)

    def delete(self, identifier: str) -> None:
        self._store.pop(identifier, None)

    def clear(self) -> None:
        """Test helper — wipe all stored secrets."""
        self._store.clear()


class EnvironmentSecretProvider(SecretProvider):
    """Read secrets from environment variables.

    The identifier is the environment variable name. The operator is
    responsible for pre-loading secrets via their secret-management
    platform (Vault, AWS Secrets Manager, Kubernetes Secrets, etc.).

    store() writes to the current process's environment — suitable for
    development and testing. In production, set the env vars externally
    and never call store().
    """

    provider_name = "environment"

    def store(self, identifier: str, value: str) -> str:
        os.environ[identifier] = value
        return identifier

    def retrieve(self, identifier: str) -> str | None:
        return os.environ.get(identifier)

    def delete(self, identifier: str) -> None:
        os.environ.pop(identifier, None)


# ── Module-level singleton (overridable in tests) ─────────────────────────────

_provider: SecretProvider = EnvironmentSecretProvider()


def get_secret_provider() -> SecretProvider:
    """Return the active secret provider (FastAPI dependency or direct call)."""
    return _provider


def set_secret_provider(provider: SecretProvider) -> None:
    """Override the active provider — used in tests and application startup."""
    global _provider  # noqa: PLW0603
    _provider = provider
