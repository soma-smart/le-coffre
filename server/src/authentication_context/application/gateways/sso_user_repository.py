from typing import Protocol, Optional
from authentication_context.domain.entities import SsoUser


class SsoUserRepository(Protocol):
    """
    Repository for managing SSO users in the authentication context.

    Handles the persistence and retrieval of SSO user mappings.
    """

    def save(self, sso_user: SsoUser) -> None: ...

    def get_by_sso_user_id(
        self, sso_user_id: str, sso_provider: str = "default"
    ) -> Optional[SsoUser]: ...

    def get_by_email(self, email: str) -> Optional[SsoUser]: ...
