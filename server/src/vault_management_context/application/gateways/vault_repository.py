from typing import Protocol

from vault_management_context.domain.entities import (
    Vault,
)


class VaultRepository(Protocol):
    def get(self) -> Vault | None: ...
    def save(self, vault: Vault) -> None: ...
