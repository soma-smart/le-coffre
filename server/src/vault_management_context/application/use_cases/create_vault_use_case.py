from typing import Optional
from uuid import UUID

from vault_management_context.domain.entities import Vault, Share
from vault_management_context.domain.value_objects import VaultConfiguration
from vault_management_context.domain.services import (
    VaultCreationService,
)
from vault_management_context.application.gateways import (
    VaultRepository,
    ShamirGateway,
    EncryptionGateway,
    VaultSessionGateway,
)
from vault_management_context.application.services import KeySessionManager
from vault_management_context.application.responses.vault_setup_response import VaultSetupResponse
from vault_management_context.application.responses.vault_status import VaultStatus


class CreateVaultUseCase:
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

    def execute(self, nb_shares: int, threshold: int, setup_id: UUID) -> VaultSetupResponse:
        existing_vault: Optional[Vault] = self.vault_repo.get()
        configuration = VaultConfiguration.create(nb_shares, threshold)

        VaultCreationService.ensure_creation_allowed(existing_vault)

        shamir_result = self.shamir_gateway.create_shares(configuration)

        encrypted_key = self.encryption_gateway.generate_vault_key(
            shamir_result.master_key
        )

        vault = VaultCreationService.create_vault_entity(configuration, encrypted_key, str(setup_id))

        # Always store the session key when creating vault
        # Clear any existing session key first (for re-setup scenario)
        if not self.vault_session_gateway.is_vault_locked():
            self.vault_session_gateway.clear_decrypted_key()
        
        KeySessionManager.decrypt_and_store_key(
            self.encryption_gateway,
            self.vault_session_gateway,
            vault.encrypted_key,
            shamir_result.master_key,
        )

        self.vault_repo.save(vault)

        return VaultSetupResponse(
            setup_id=str(setup_id),
            shares=shamir_result.shares
        )
