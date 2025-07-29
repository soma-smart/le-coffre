from typing import Optional, Protocol

from src.vault_management_context.business_logic.models.value_objects.vault import (
    Vault,
)


class VaultRepository(Protocol):
    def get(self) -> Optional[Vault]: ...
    def save(self, vault: Vault) -> None: ...
