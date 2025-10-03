from typing import Optional
from uuid import UUID

from authentication_context.domain.entities import UserPassword


class FakeUserPasswordRepository:
    def __init__(self):
        self._user_passwords = {}

    def save(self, user_password: UserPassword) -> None:
        self._user_passwords[user_password.id] = user_password

    def get_by_id(self, id: UUID) -> Optional[UserPassword]:
        return self._user_passwords.get(id)

    def get_by_email(self, email: str) -> Optional[UserPassword]:
        for user_password in self._user_passwords.values():
            if user_password.email == email:
                return user_password
        return None
