from typing import Optional

from vault_management_context.domain.entities import Vault
from vault_management_context.application.gateways import (
    VaultRepository,
)
from vault_management_context.domain.exceptions import (
    NoVaultExisting,
    VaultAlreadySetuped,
    VaultSetupIdNotFound,
)


class ValidateVaultSetupUseCase:
    def __init__(
        self,
        vault_repo: VaultRepository,
        shamir_gateway=None,  # Not used in this simplified version
        encryption_gateway=None,  # Not used in this simplified version
        vault_session_gateway=None,  # Not used in this simplified version
    ) -> None:
        self.vault_repo = vault_repo

    def execute(self, setup_id: str) -> None:
        """Validate and complete vault setup
        
        Args:
            setup_id: The unique setup identifier from the initial setup
            
        Raises:
            NoVaultExisting: If no vault exists
            VaultAlreadySetuped: If vault is not in pending state
            VaultSetupIdNotFound: If setup_id doesn't match
        """
        existing_vault: Optional[Vault] = self.vault_repo.get()
        
        if existing_vault is None:
            raise NoVaultExisting()
            
        if existing_vault.status != "PENDING":
            raise VaultAlreadySetuped()
            
        if existing_vault.setup_id != setup_id:
            raise VaultSetupIdNotFound()
        
        # Vault is valid and in pending state, complete the setup
        # Set status to COMPLETED (vault setup is done, but vault might be locked/unlocked based on session)
        existing_vault.status = "COMPLETED"
        self.vault_repo.save(existing_vault)