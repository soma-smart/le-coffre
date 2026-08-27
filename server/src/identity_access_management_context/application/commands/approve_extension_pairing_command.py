from dataclasses import dataclass

from shared_kernel.domain.entities import ValidatedUser


@dataclass
class ApproveExtensionPairingCommand:
    user_code: str
    requesting_user: ValidatedUser
