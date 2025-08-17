from vault_management_context.application.gateways import (
    VaultRepository,
    VaultSessionGateway,
)
from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    VaultLockedException,
)


class LockVaultUseCase:
    def __init__(
        self,
        vault_repository: VaultRepository,
        vault_session_gateway: VaultSessionGateway,
    ):
        self._vault_repository = vault_repository
        self._vault_session_gateway = vault_session_gateway

    def execute(self) -> None:
        """Lock the vault by clearing the decrypted key from memory"""
        vault = self._vault_repository.get()
        if vault is None:
            raise VaultNotSetupException()

        try:
            self._vault_session_gateway.get_decrypted_key()
        except ValueError:
            raise VaultLockedException()

        self._vault_session_gateway.clear_decrypted_key()
