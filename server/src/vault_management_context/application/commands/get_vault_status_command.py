from dataclasses import dataclass

from vault_management_context.domain.value_objects import UnlockSessionId


@dataclass
class GetVaultStatusCommand:
    # When given, a locked vault reports PENDING_UNLOCK if this unlock session
    # already holds shares. Without it, a locked vault is simply LOCKED.
    session_id: UnlockSessionId | None = None
