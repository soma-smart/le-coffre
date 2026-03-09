from typing import Protocol

from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import VaultConfiguration
from vault_management_context.domain.value_objects.shamir_result import ShamirResult


class ShamirGateway(Protocol):
    def create_shares(self, configuration: VaultConfiguration) -> ShamirResult:
        """Create Shamir shares and return them with the master key

        Args:
            configuration: The vault configuration

        Returns:
            ShamirResult containing shares and master key
        """
        ...

    def reconstruct_secret(self, shares: list[Share]) -> str:
        """Reconstruct the master secret from shares

        Args:
            shares: List of Shamir shares

        Returns:
            The reconstructed master key
        """
        ...
