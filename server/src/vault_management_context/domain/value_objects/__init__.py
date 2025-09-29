"""Value Objects for the Vault Management context."""

from .vault_configuration import VaultConfiguration
from .shamir_result import ShamirResult

__all__ = ["VaultConfiguration", "ShamirResult"]
