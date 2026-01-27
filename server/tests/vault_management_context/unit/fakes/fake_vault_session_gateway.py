from vault_management_context.application.gateways import VaultSessionGateway
from vault_management_context.domain.exceptions import VaultUnlockedError


class FakeVaultSessionGateway(VaultSessionGateway):
    def __init__(self):
        self._decrypted_key: str | None = None

    def store_decrypted_key(self, decrypted_key: str) -> None:
        if self._decrypted_key is not None:
            raise VaultUnlockedError()
        self._decrypted_key = decrypted_key

    def get_decrypted_key(self) -> str:
        if self._decrypted_key is None:
            raise ValueError("No decrypted key stored in memory")
        return self._decrypted_key

    def clear_decrypted_key(self) -> None:
        self._decrypted_key = None

    def is_vault_locked(self) -> bool:
        return self._decrypted_key is None
