"""Value Objects for the Vault Management context."""

from .shamir_result import ShamirResult
from .vault_configuration import VaultConfiguration

__all__ = ["VaultConfiguration", "ShamirResult"]
