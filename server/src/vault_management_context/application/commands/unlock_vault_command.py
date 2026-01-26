from dataclasses import dataclass
from typing import List
from vault_management_context.domain.entities import Share


@dataclass
class UnlockVaultCommand:
    shares: List[Share]
