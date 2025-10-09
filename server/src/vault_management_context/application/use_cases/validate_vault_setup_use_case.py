from typing import Optional

from vault_management_context.domain.entities import Vault
from vault_management_context.application.gateways import (
    VaultRepository,
)
from vault_management_context.domain.exceptions import VaultManagementDomainError


class VaultSetupValidationError(VaultManagementDomainError):
    def __init__(self, message: str = "Invalid setup ID or vault not in pending state"):
        super().__init__(message)


class ValidateVaultSetupUseCase:
    def __init__(
        self,
        vault_repo: VaultRepository,
        shamir_gateway=None,  # Not needed for validation
        encryption_gateway=None,  # Not needed for validation
        vault_session_gateway=None,  # Not needed for validation
    ) -> None:
        self.vault_repo = vault_repo

    def execute(self, setup_id: str) -> None:
        """Validate and complete vault setup
        
        Args:
            setup_id: The unique setup identifier from the initial setup
            
        Raises:
            VaultSetupValidationError: If setup_id is invalid or vault not in pending state
        """
        existing_vault: Optional[Vault] = self.vault_repo.get()
        
        if existing_vault is None:
            raise VaultSetupValidationError("No vault found")
            
        if existing_vault.status != "PENDING":
            raise VaultSetupValidationError("Vault is not in pending state")
            
        if existing_vault.setup_id != setup_id:
            raise VaultSetupValidationError("Invalid setup ID")
        
        # Vault is valid and in pending state, complete the setup
        existing_vault.status = "SETUPED"
        self.vault_repo.save(existing_vault)