from typing import Optional, Dict
from authentication_context.domain.entities.sso_user import SsoUser


class FakeSsoUserRepository:
    def __init__(self):
        self._users: Dict[str, SsoUser] = {}

    def save(self, sso_user: SsoUser) -> None:
        key = f"{sso_user.sso_user_id}:{sso_user.sso_provider}"
        self._users[key] = sso_user

    def get_by_sso_user_id(
        self, sso_user_id: str, sso_provider: str = "default"
    ) -> Optional[SsoUser]:
        key = f"{sso_user_id}:{sso_provider}"
        return self._users.get(key)

    def get_by_email(self, email: str) -> Optional[SsoUser]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def clear(self) -> None:
        """Helper method for tests to clear all users"""
        self._users.clear()
