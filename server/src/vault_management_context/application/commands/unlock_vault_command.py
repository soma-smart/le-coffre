from dataclasses import dataclass

from vault_management_context.domain.entities import Share


@dataclass
class UnlockVaultCommand:
    shares: list[Share]
