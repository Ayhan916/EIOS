"""EIOS secret provider infrastructure (M40.1 / M40.2)."""

from .aws_provider import AwsSecretsManagerProvider, SecretsManagerClient
from .provider import (
    EnvironmentSecretProvider,
    InMemorySecretProvider,
    SecretProvider,
    get_secret_provider,
    set_secret_provider,
)
from .vault_provider import VaultClient, VaultSecretProvider

__all__ = [
    "SecretProvider",
    "InMemorySecretProvider",
    "EnvironmentSecretProvider",
    "get_secret_provider",
    "set_secret_provider",
    "VaultSecretProvider",
    "VaultClient",
    "AwsSecretsManagerProvider",
    "SecretsManagerClient",
]
