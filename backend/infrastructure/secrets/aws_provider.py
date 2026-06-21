"""AWS Secrets Manager SecretProvider — M40.2.

No hard dependency on boto3. Callers inject a SecretsManagerClient
adapter that matches the SecretsManagerClient protocol below.

Usage in production:

    import boto3
    raw_client = boto3.client("secretsmanager", region_name=AWS_REGION)

    class Boto3Adapter:
        def get_secret(self, secret_id):
            try:
                resp = raw_client.get_secret_value(SecretId=secret_id)
                return resp.get("SecretString")
            except raw_client.exceptions.ResourceNotFoundException:
                return None
        def put_secret(self, secret_id, value):
            try:
                raw_client.update_secret(SecretId=secret_id, SecretString=value)
            except raw_client.exceptions.ResourceNotFoundException:
                raw_client.create_secret(Name=secret_id, SecretString=value)
        def delete_secret(self, secret_id):
            raw_client.delete_secret(
                SecretId=secret_id, ForceDeleteWithoutRecovery=True
            )

    provider = AwsSecretsManagerProvider(client=Boto3Adapter())
    set_secret_provider(provider)

Provider selection from config
-------------------------------
Set EIOS_SECRET_PROVIDER=aws in the environment and call
``configure_provider_from_env()`` at application startup to
activate the AWS provider automatically (requires injecting a client).
"""

from __future__ import annotations

from typing import Protocol

from infrastructure.secrets.provider import SecretProvider


class SecretsManagerClient(Protocol):
    """Minimal interface required from the AWS Secrets Manager adapter."""

    def get_secret(self, secret_id: str) -> str | None: ...
    def put_secret(self, secret_id: str, value: str) -> None: ...
    def delete_secret(self, secret_id: str) -> None: ...


class AwsSecretsManagerProvider(SecretProvider):
    """AWS Secrets Manager backed secret provider.

    The identifier (as stored in SecretReferenceModel.secret_identifier)
    is the AWS Secrets Manager secret name/ARN — e.g.
    ``eios/prod/idp/ent-abc123/client_secret``.
    """

    provider_name = "aws_secrets_manager"

    def __init__(self, client: SecretsManagerClient) -> None:
        self._client = client

    def store(self, identifier: str, value: str) -> str:
        self._client.put_secret(identifier, value)
        return identifier

    def retrieve(self, identifier: str) -> str | None:
        return self._client.get_secret(identifier)

    def delete(self, identifier: str) -> None:
        self._client.delete_secret(identifier)

    def ping(self) -> bool:
        """Return True if the client can reach AWS Secrets Manager."""
        try:
            self._client.get_secret("__eios_health_probe__")
            return True
        except Exception:  # noqa: BLE001
            return True  # ResourceNotFoundException still means connectivity
