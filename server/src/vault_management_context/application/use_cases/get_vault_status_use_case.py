from typing import Optional

from vault_management_context.application.commands import GetVaultStatusCommand
from vault_management_context.application.gateways import (
    VaultSessionGateway,
    VaultRepository,
    ShareRepository,
)
from vault_management_context.application.responses import VaultStatus
from vault_management_context.domain.entities.vault import Vault


class GetVaultStatusUseCase:
    def __init__(
        self,
        vault_repository: VaultRepository,
        vault_session_gateway: VaultSessionGateway,
        share_repository: ShareRepository,
    ) -> None:
        self.vault_repository = vault_repository
        self.vault_session_gateway = vault_session_gateway
        self.share_repository = share_repository

    def execute(self, command: GetVaultStatusCommand) -> VaultStatus:
        existing_vault: Optional[Vault] = self.vault_repository.get()
        if existing_vault is None:
            return VaultStatus.NOT_SETUP

        is_locked = self.vault_session_gateway.is_vault_locked()
        if is_locked:
            shares = self.share_repository.get_all()
            if len(shares) > 0:
                return VaultStatus.PENDING_UNLOCK
            return VaultStatus.LOCKED
        return VaultStatus.UNLOCKED
