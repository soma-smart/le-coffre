from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlmodel import Session

from identity_access_management_context.adapters.secondary.sql import SqlUserRepository


@dataclass(frozen=True)
class UserContact:
    user_id: UUID
    email: str
    display_name: str


class UserContactInfoApi:
    """Private API for other bounded contexts to get how to reach a set of users.

    Like GroupOwnershipInfoApi, it manages its own DB session per call via a
    session_maker, so it can be built once at startup for an event subscriber.
    """

    def __init__(self, session_maker: Callable[[], Session]):
        self._session_maker = session_maker

    def get_contacts(self, user_ids: list[UUID]) -> list[UserContact]:
        """Contacts of the users that still exist, in the given order; unknown ids are skipped."""
        with self._session_maker() as session:
            # One round trip for all the ids, rather than one query per id: this is called
            # with the full list of opted-in recipients on every vault lock/unlock.
            users_by_id = {user.id: user for user in SqlUserRepository(session).get_by_ids(user_ids)}
            return [
                UserContact(user_id=user.id, email=user.email, display_name=user.name)
                for user_id in user_ids
                if (user := users_by_id.get(user_id)) is not None
            ]
