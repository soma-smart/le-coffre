from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlmodel import Session

from identity_access_management_context.adapters.secondary.sql import SqlUserRepository
from identity_access_management_context.application.commands import GetUserCommand
from identity_access_management_context.application.use_cases import GetUserUseCase
from identity_access_management_context.domain.exceptions import UserNotFoundError


@dataclass
class UserContactInfo:
    email: str
    display_name: str


class UserContactInfoApi:
    """Private API for other bounded contexts to reach a user by email.

    Like GroupOwnershipInfoApi, it manages its own session per call from a
    session_maker given at construction, so an event subscriber built once at
    startup can use it outside any request.
    """

    def __init__(self, session_maker: Callable[[], Session]):
        self._session_maker = session_maker

    def get_contact(self, user_id: UUID) -> UserContactInfo | None:
        with self._session_maker() as session:
            try:
                user = GetUserUseCase(SqlUserRepository(session)).execute(GetUserCommand(user_id=user_id))
            except UserNotFoundError:
                return None
            return UserContactInfo(email=user.email, display_name=user.name)
