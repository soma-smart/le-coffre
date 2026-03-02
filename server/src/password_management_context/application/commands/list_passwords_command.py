from dataclasses import dataclass

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class ListPasswordsCommand:
    requester: AuthenticatedUser
    folder: str | None = None
