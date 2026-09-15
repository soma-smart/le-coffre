from dataclasses import dataclass

from shared_kernel.domain.entities import ValidatedUser


@dataclass
class RevokeAllExtensionTokensCommand:
    requesting_user: ValidatedUser
