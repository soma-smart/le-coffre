from typing import Optional

from vault_management_context.domain.entities import Vault
from vault_management_context.application.gateways.vault_repository import (
    VaultRepository,
)


class FakeVaultRepository(VaultRepository):
    def __init__(self):
        self._vault = None

    def get(self) -> Optional[Vault]:
        return self._vault

    def save(self, vault: Vault) -> None:
        self._vault = vault

    def save_vault_with_shares(
        self, nb_shares: int, threshold: int, encrypted_key: str = "test_key"
    ) -> None:
        self._vault = Vault(
            nb_shares=nb_shares, 
            threshold=threshold, 
            encrypted_key=encrypted_key,
            setup_id=None,
            status="PENDING"
        )
