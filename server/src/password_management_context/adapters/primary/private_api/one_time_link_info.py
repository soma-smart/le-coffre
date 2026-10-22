from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from uuid import UUID

from sqlmodel import Session

from password_management_context.adapters.secondary.sql import SqlOneTimeLinkRepository, SqlPasswordRepository
from password_management_context.domain.exceptions import PasswordNotFoundError


@dataclass(frozen=True)
class OneTimeLinkInfo:
    """What another context may know about a one-time link: never its token."""

    link_id: UUID
    created_by_user_id: UUID
    password_name: str
    expires_at: datetime
    read_at: datetime | None
    revoked_at: datetime | None


class OneTimeLinkInfoApi:
    """Private API for other bounded contexts to look up one one-time link.

    Like UserContactInfoApi, it manages its own DB session per call from a
    session_maker given at construction, so it can be used outside any request
    (by an event subscriber or a background sweep).
    """

    def __init__(self, session_maker: Callable[[], Session]):
        self._session_maker = session_maker

    def get_link(self, link_id: UUID) -> OneTimeLinkInfo | None:
        """The link, or None if it does not exist (any more) or its password is gone."""
        with self._session_maker() as session:
            link = SqlOneTimeLinkRepository(session).get_by_id(link_id)
            if link is None:
                return None
            try:
                password = SqlPasswordRepository(session).get_by_id(link.password_id)
            except PasswordNotFoundError:
                return None
            return OneTimeLinkInfo(
                link_id=link.id,
                created_by_user_id=link.created_by_user_id,
                password_name=password.name,
                expires_at=link.expires_at,
                read_at=link.read_at,
                revoked_at=link.revoked_at,
            )
