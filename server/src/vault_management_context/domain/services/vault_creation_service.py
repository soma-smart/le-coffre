from typing import List, Optional

from vault_management_context.domain.entities import Vault, Share
from vault_management_context.domain.value_objects import VaultConfiguration
from vault_management_context.domain.exceptions import VaultAlreadyExistsError


class VaultCreationService:
    @staticmethod
    def ensure_creation_allowed(existing_vault: Optional[Vault]) -> None:
        """Validate that vault creation is allowed according to business rules

        Args:
            existing_vault: Any existing vault to check against

        Raises:
            VaultAlreadyExistsError: If a vault already exists for this organization
        """
        if existing_vault is not None:
            raise VaultAlreadyExistsError()

    @staticmethod
    def create_vault_entity(
        configuration: VaultConfiguration, shares: List[Share]
    ) -> Vault:
        """Create a vault entity with the given configuration and shares

        Args:
            configuration: The validated vault configuration
            shares: The cryptographically generated shares

        Returns:
            The created vault entity
        """
        return Vault(
            nb_shares=configuration.share_count.value,
            threshold=configuration.threshold.value,
            shares=shares,
        )
