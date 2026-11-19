from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class AuthenticateTokenResponse:
    principal_id: UUID
    principal_kind: Literal["user", "service_account"]
    roles: list[str]
    """The principal's roles: a user's, none for a service account."""
    credential_id: UUID
    read_only: bool
