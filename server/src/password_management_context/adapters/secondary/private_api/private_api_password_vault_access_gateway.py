from password_management_context.application.gateways import PasswordVaultAccessGateway
from password_management_context.domain.exceptions import PasswordEncryptionUnavailableError
from vault_management_context.adapters.primary.private_api import VaultStatusApi
from vault_management_context.domain.exceptions import VaultManagementDomainError


class PrivateApiPasswordVaultAccessGateway(PasswordVaultAccessGateway):
    def __init__(self, vault_status_api: VaultStatusApi):
        self._vault_status_api = vault_status_api

    def ensure_vault_is_unlocked(self) -> None:
        try:
            self._vault_status_api.ensure_vault_is_unlocked()
        except VaultManagementDomainError as e:
            raise PasswordEncryptionUnavailableError() from e
