from typing import Optional

from src.vault_management_context.business_logic.models.value_objects.vault import (
    Vault,
)
from src.vault_management_context.business_logic.gateways.vault_repository import (
    VaultRepository,
)


class FakeVaultRepository(VaultRepository):
    def __init__(self):
        self._vault = None

    def get(self) -> Optional[Vault]:
        return self._vault

    def save(self, vault: Vault) -> None:
        self._vault = vault
