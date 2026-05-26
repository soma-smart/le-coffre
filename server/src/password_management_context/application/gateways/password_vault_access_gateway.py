from typing import Protocol


class PasswordVaultAccessGateway(Protocol):
    def ensure_vault_is_unlocked(self) -> None:
        """Raises when password operations should be blocked because the vault is locked."""
        ...
