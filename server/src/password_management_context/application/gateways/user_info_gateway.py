from typing import Protocol
from uuid import UUID


class UserInfoGateway(Protocol):
    """Gateway to retrieve user information from IAM context"""

    def get_user_email(self, user_id: UUID) -> str | None:
        """Get email address for a user"""
        ...

    def get_group_name(self, group_id: UUID) -> str | None:
        """Get name for a group"""
        ...
