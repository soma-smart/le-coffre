from vault_management_context.application.gateways import VaultSessionGateway
from vault_management_context.domain.exceptions import VaultUnlockedError


class InMemoryVaultSessionGateway(VaultSessionGateway):
    def __init__(self):
        self._decrypted_key: bytearray | None = None

    def store_decrypted_key(self, decrypted_key: str) -> None:
        if self._decrypted_key is not None:
            raise VaultUnlockedError()
        self._decrypted_key = bytearray.fromhex(decrypted_key)

    def get_decrypted_key(self) -> str:
        if self._decrypted_key is None:
            raise ValueError("No decrypted key stored in memory")
        return self._decrypted_key.hex()

    def clear_decrypted_key(self) -> None:
        if self._decrypted_key is not None:
            for i in range(len(self._decrypted_key)):
                self._decrypted_key[i] = 0
        self._decrypted_key = None

    def is_vault_locked(self) -> bool:
        return self._decrypted_key is None
