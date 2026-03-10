from datetime import datetime
from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import SsoUser


class SsoUserRepository(Protocol):
    """
    Repository for managing SSO users in the authentication context.

    Handles the persistence and retrieval of SSO user mappings.
    """

    def create(self, sso_user: SsoUser) -> None: ...

    def update_last_login(self, sso_user_id: str, sso_provider: str, last_login: datetime) -> None: ...

    def get_by_sso_user_id(self, sso_user_id: str, sso_provider: str = "default") -> SsoUser | None: ...

    def get_by_user_id(self, user_id: UUID) -> SsoUser | None: ...
