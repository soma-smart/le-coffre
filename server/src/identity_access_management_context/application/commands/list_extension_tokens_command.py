from dataclasses import dataclass

from shared_kernel.domain.entities import ValidatedUser


@dataclass
class ListExtensionTokensCommand:
    requesting_user: ValidatedUser
