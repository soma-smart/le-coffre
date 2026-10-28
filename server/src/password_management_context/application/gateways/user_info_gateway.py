from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PrincipalInfo:
    """How a principal is shown as the actor of an event."""

    kind: str
    """`user` or `service_account`."""
    display_name: str


class UserInfoGateway(Protocol):
    """Gateway to retrieve user information from IAM context"""

    def get_principal(self, principal_id: UUID) -> PrincipalInfo | None:
        """Name a principal of any kind (user, service account), None if it no longer exists"""
        ...

    def get_user_display_name(self, user_id: UUID) -> str | None:
        """Get the display name for a user"""
        ...

    def get_group_name(self, group_id: UUID) -> str | None:
        """Get name for a group"""
        ...
