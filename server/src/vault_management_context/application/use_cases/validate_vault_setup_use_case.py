from typing import Optional

from vault_management_context.domain.entities import Vault
from vault_management_context.application.gateways import (
    VaultRepository,
    VaultSessionGateway,
    EncryptionGateway,
    ShamirGateway,
)
from vault_management_context.application.services import KeySessionManager
from vault_management_context.domain.exceptions import VaultManagementDomainError


class VaultSetupValidationError(VaultManagementDomainError):
    def __init__(self, message: str = "Invalid setup ID or vault not in pending state"):
        super().__init__(message)


class ValidateVaultSetupUseCase:
    def __init__(
        self,
        vault_repo: VaultRepository,
        shamir_gateway: ShamirGateway,
        encryption_gateway: EncryptionGateway,
        vault_session_gateway: VaultSessionGateway,
    ) -> None:
        self.vault_repo = vault_repo
        self.shamir_gateway = shamir_gateway
        self.encryption_gateway = encryption_gateway
        self.vault_session_gateway = vault_session_gateway

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
        # We need to regenerate the master key from the configuration
        # This is a simplified approach - in practice you might want to store encrypted shares
        from vault_management_context.domain.value_objects import VaultConfiguration
        
        configuration = VaultConfiguration.create(existing_vault.nb_shares, existing_vault.threshold)
        shamir_result = self.shamir_gateway.create_shares(configuration)
        
        # Store the session key now that validation is complete
        KeySessionManager.decrypt_and_store_key(
            self.encryption_gateway,
            self.vault_session_gateway,
            existing_vault.encrypted_key,
            shamir_result.master_key,
        )
        
        # Update vault status to completed
        existing_vault.status = "SETUPED"
        self.vault_repo.save(existing_vault)