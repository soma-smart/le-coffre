from dataclasses import dataclass

from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import UnlockSessionId


@dataclass
class UnlockVaultCommand:
    session_id: UnlockSessionId
    shares: list[Share]
