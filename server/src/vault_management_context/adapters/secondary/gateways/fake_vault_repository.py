from typing import Optional

from vault_management_context.domain.entities import (
    Vault,
)
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
