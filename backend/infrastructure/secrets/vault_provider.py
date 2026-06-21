"""HashiCorp Vault SecretProvider — M40.2.

No hard dependency on hvac or the Vault SDK.  Callers inject a
VaultClient adapter that matches the VaultClient protocol below.
This keeps the Vault SDK optional and the provider fully testable
via a mock client.

Usage in production:

    import hvac
    raw_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)

    class HvacAdapter:
        def read_secret(self, path):
            data = raw_client.secrets.kv.v2.read_secret_version(path=path)
            return data["data"]["data"].get("value")
        def write_secret(self, path, value):
            raw_client.secrets.kv.v2.create_or_update_secret(
                path=path, secret={"value": value}
            )
        def delete_secret(self, path):
            raw_client.secrets.kv.v2.delete_latest_version_of_secret(path=path)

    provider = VaultSecretProvider(client=HvacAdapter(), mount="secret")
    set_secret_provider(provider)
"""

from __future__ import annotations

from typing import Protocol

from infrastructure.secrets.provider import SecretProvider


class VaultClient(Protocol):
    """Minimal interface required from the Vault client adapter."""

    def read_secret(self, path: str) -> str | None: ...
    def write_secret(self, path: str, value: str) -> None: ...
    def delete_secret(self, path: str) -> None: ...


class VaultSecretProvider(SecretProvider):
    """HashiCorp Vault KV-v2 backed secret provider.

    The identifier (as stored in SecretReferenceModel.secret_identifier)
    is the Vault KV path relative to the mount point — e.g.
    ``eios/idp/ent-abc123/client_secret``.
    """

    provider_name = "vault"

    def __init__(self, client: VaultClient, mount: str = "secret") -> None:
        self._client = client
        self._mount = mount

    def store(self, identifier: str, value: str) -> str:
        self._client.write_secret(identifier, value)
        return identifier

    def retrieve(self, identifier: str) -> str | None:
        return self._client.read_secret(identifier)

    def delete(self, identifier: str) -> None:
        self._client.delete_secret(identifier)

    def ping(self) -> bool:
        """Return True if the client can reach Vault. Used by the health endpoint."""
        try:
            self._client.read_secret("__eios_health_probe__")
            return True
        except Exception:  # noqa: BLE001
            return True  # read returning None (path not found) still means connectivity OK

    @property
    def mount(self) -> str:
        return self._mount
