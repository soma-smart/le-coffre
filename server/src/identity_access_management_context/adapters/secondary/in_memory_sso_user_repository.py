from typing import Optional, Dict
from uuid import UUID
from identity_access_management_context.domain.entities.sso_user import SsoUser


class InMemorySsoUserRepository:
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

    def get_by_user_id(self, user_id: UUID) -> Optional[SsoUser]:
        for user in self._users.values():
            if user.internal_user_id == user_id:
                return user
        return None
