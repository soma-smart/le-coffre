import threading

from vault_management_context.application.gateways import VaultSessionGateway
from vault_management_context.domain.exceptions import VaultIsLockedError, VaultUnlockedError


class InMemoryVaultSessionGateway(VaultSessionGateway):
    def __init__(self):
        self._decrypted_key: str | None = None
        # Requests run in a thread pool: without a lock, two concurrent unlocks (or
        # locks) could both pass the check and each publish an event — and send
        # the vault lock/unlock notification emails twice.
        self._lock = threading.Lock()

    def store_decrypted_key(self, decrypted_key: str) -> None:
        with self._lock:
            if self._decrypted_key is not None:
                raise VaultUnlockedError()
            self._decrypted_key = decrypted_key

    def get_decrypted_key(self) -> str:
        key = self._decrypted_key
        if key is None:
            raise VaultIsLockedError()
        return key

    def clear_decrypted_key(self) -> bool:
        with self._lock:
            was_unlocked = self._decrypted_key is not None
            self._decrypted_key = None
            return was_unlocked

    def is_vault_locked(self) -> bool:
        return self._decrypted_key is None
