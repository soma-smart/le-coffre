from vault_management_context.application.commands import UnlockVaultCommand
from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    ShareReconstructionError,
    VaultUnlockedError,
)
from vault_management_context.application.gateways import (
    VaultRepository,
    ShamirGateway,
    EncryptionGateway,
    VaultSessionGateway,
    ShareRepository,
)
from vault_management_context.application.services import KeySessionManager


class UnlockVaultUseCase:
    def __init__(
        self,
        vault_repository: VaultRepository,
        shamir_gateway: ShamirGateway,
        encryption_gateway: EncryptionGateway,
        vault_session_gateway: VaultSessionGateway,
        share_repository: ShareRepository,
    ):
        self._vault_repository = vault_repository
        self._shamir_gateway = shamir_gateway
        self._encryption_gateway = encryption_gateway
        self._vault_session_gateway = vault_session_gateway
        self._share_repository = share_repository

    def execute(self, command: UnlockVaultCommand) -> None:
        vault = self._vault_repository.get()
        if vault is None:
            raise VaultNotSetupException()

        try:
            existing_shares = self._share_repository.get_all()
            all_shares = existing_shares + command.shares

            master_secret = self._shamir_gateway.reconstruct_secret(all_shares)

            KeySessionManager.decrypt_and_store_key(
                self._encryption_gateway,
                self._vault_session_gateway,
                vault.encrypted_key,
                master_secret,
            )

            self._share_repository.clear()
        except VaultUnlockedError as e:
            raise e
        except Exception as e:
            self._share_repository.add(command.shares)
            raise ShareReconstructionError() from e
