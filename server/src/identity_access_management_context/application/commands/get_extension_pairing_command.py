from dataclasses import dataclass

from shared_kernel.domain.entities import ValidatedUser


@dataclass
class GetExtensionPairingCommand:
    """Cookie-authenticated. Backs the approval page."""

    user_code: str
    requesting_user: ValidatedUser
