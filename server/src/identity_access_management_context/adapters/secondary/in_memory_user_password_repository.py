from typing import Optional, Dict
from uuid import UUID

from identity_access_management_context.application.gateways import UserPasswordRepository
from identity_access_management_context.domain.entities import UserPassword


class InMemoryUserPasswordRepository:
    def __init__(self):
        self._users: Dict[UUID, UserPassword] = {}
        self._users_by_email: Dict[str, UserPassword] = {}

    def save(self, user_password: UserPassword) -> None:
        self._users[user_password.id] = user_password
        self._users_by_email[user_password.email] = user_password

    def get_by_id(self, id: UUID) -> Optional[UserPassword]:
        return self._users.get(id)

    def get_by_email(self, email: str) -> Optional[UserPassword]:
        return self._users_by_email.get(email)
