from typing import List

from vault_management_context.domain.entities import Share
from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    ShareReconstructionError,
    VaultUnlockedError,
)
from vault_management_context.application.gateways import VaultRepository, ShamirGateway
from vault_management_context.application.gateways import (
    EncryptionGateway,
    VaultSessionGateway,
)
from vault_management_context.application.services import KeySessionManager
from shared_kernel.authentication import AuthenticatedUser, AdminPermissionChecker


class UnlockVaultUseCase:
    def __init__(
        self,
        vault_repository: VaultRepository,
        shamir_gateway: ShamirGateway,
        encryption_gateway: EncryptionGateway,
        vault_session_gateway: VaultSessionGateway,
    ):
        self._vault_repository = vault_repository
        self._shamir_gateway = shamir_gateway
        self._encryption_gateway = encryption_gateway
        self._vault_session_gateway = vault_session_gateway

    def execute(self, shares: List[Share], requesting_user: AuthenticatedUser) -> None:
        AdminPermissionChecker.ensure_admin(requesting_user, "unlock the vault")

        vault = self._vault_repository.get()
        if vault is None:
            raise VaultNotSetupException()

        try:
            master_secret = self._shamir_gateway.reconstruct_secret(shares)

            KeySessionManager.decrypt_and_store_key(
                self._encryption_gateway,
                self._vault_session_gateway,
                vault.encrypted_key,
                master_secret,
            )
        except VaultUnlockedError as e:
            raise e
        except Exception as e:
            raise ShareReconstructionError() from e
