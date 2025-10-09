from typing import Optional
from vault_management_context.application.gateways import (
    VaultSessionGateway,
    VaultRepository,
)
from vault_management_context.application.responses import VaultStatus
from vault_management_context.domain.entities.vault import Vault


class GetVaultStatusUseCase:
    def __init__(
        self,
        vault_repository: VaultRepository,
        vault_session_gateway: VaultSessionGateway,
    ) -> None:
        self.vault_repository = vault_repository
        self.vault_session_gateway = vault_session_gateway

    def execute(self) -> VaultStatus:
        existing_vault: Optional[Vault] = self.vault_repository.get()
        if existing_vault is None:
            return VaultStatus.NOT_SETUP

        if existing_vault.status == "PENDING":
            return VaultStatus.PENDING

        # For COMPLETED or any other status, check session state
        is_locked = self.vault_session_gateway.is_vault_locked()
        if is_locked:
            return VaultStatus.LOCKED
        return VaultStatus.UNLOCKED
