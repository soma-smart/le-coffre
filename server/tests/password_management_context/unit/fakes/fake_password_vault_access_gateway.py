from password_management_context.application.gateways import PasswordVaultAccessGateway
from password_management_context.domain.exceptions import PasswordEncryptionUnavailableError


class FakePasswordVaultAccessGateway(PasswordVaultAccessGateway):
    def __init__(self):
        self._is_locked = False

    def ensure_vault_is_unlocked(self) -> None:
        if self._is_locked:
            raise PasswordEncryptionUnavailableError()

    def lock(self) -> None:
        self._is_locked = True

    def unlock(self) -> None:
        self._is_locked = False
