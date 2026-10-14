from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlmodel import Session

from identity_access_management_context.adapters.secondary.sql import SqlUserRepository
from identity_access_management_context.application.commands import GetUserCommand
from identity_access_management_context.application.use_cases import GetUserUseCase
from identity_access_management_context.domain.exceptions import UserNotFoundError


@dataclass(frozen=True)
class UserContactInfo:
    user_id: UUID
    email: str
    display_name: str


class UserContactInfoApi:
    """Private API for other bounded contexts to get how to reach one or more users.

    Like GroupOwnershipInfoApi, it manages its own DB session per call from a
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
            return UserContactInfo(user_id=user.id, email=user.email, display_name=user.name)

    def get_contacts(self, user_ids: list[UUID]) -> list[UserContactInfo]:
        """Contacts of the users that still exist, in the given order; unknown ids are skipped."""
        with self._session_maker() as session:
            # One round trip for all the ids, rather than one query per id: this is called
            # with the full list of opted-in recipients on every vault lock/unlock.
            users_by_id = {user.id: user for user in SqlUserRepository(session).get_by_ids(user_ids)}
            return [
                UserContactInfo(user_id=user.id, email=user.email, display_name=user.name)
                for user_id in user_ids
                if (user := users_by_id.get(user_id)) is not None
            ]
