from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from identity_access_management_context.domain.entities.sso_user import SsoUser
from identity_access_management_context.domain.exceptions import (
    SsoUserAlreadyExistsException,
)


class InMemorySsoUserRepository:
    def __init__(self):
        self._users: Dict[str, SsoUser] = {}

    def create(self, sso_user: SsoUser) -> None:
        key = f"{sso_user.sso_user_id}:{sso_user.sso_provider}"
        if key in self._users:
            raise SsoUserAlreadyExistsException(
                f"SSO user {sso_user.sso_user_id} with provider {sso_user.sso_provider} already exists"
            )
        self._users[key] = sso_user

    def update_last_login(
        self, sso_user_id: str, sso_provider: str, last_login: datetime
    ) -> None:
        key = f"{sso_user_id}:{sso_provider}"
        if key in self._users:
            self._users[key].last_login = last_login

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
