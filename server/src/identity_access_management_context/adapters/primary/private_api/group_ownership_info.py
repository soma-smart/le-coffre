from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlmodel import Session

from identity_access_management_context.adapters.secondary.sql import (
    SqlGroupMemberRepository,
    SqlGroupRepository,
    SqlUserRepository,
)
from identity_access_management_context.application.commands import (
    GetGroupCommand,
    GetUserCommand,
)
from identity_access_management_context.application.use_cases import (
    GetGroupUseCase,
    GetUserUseCase,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotFoundError,
)


@dataclass
class GroupOwnerInfo:
    email: str
    display_name: str
    group_name: str


class GroupOwnershipInfoApi:
    """Private API for other bounded contexts to query group ownership details.

    Unlike UserInfoApi, this manages its own DB session per call via a session_maker
    given at construction, so it can be built once at startup for a non-request-scoped
    caller (an event subscriber) instead of wired per-request through FastAPI Depends.
    """

    def __init__(self, session_maker: Callable[[], Session]):
        self._session_maker = session_maker

    def get_owner_info(self, user_id: UUID, group_id: UUID) -> GroupOwnerInfo | None:
        with self._session_maker() as session:
            try:
                user = GetUserUseCase(SqlUserRepository(session)).execute(GetUserCommand(user_id=user_id))
                group_response = GetGroupUseCase(
                    SqlGroupRepository(session), SqlGroupMemberRepository(session)
                ).execute(GetGroupCommand(group_id=group_id))
            except (UserNotFoundError, GroupNotFoundException):
                return None
            return GroupOwnerInfo(email=user.email, display_name=user.name, group_name=group_response.group.name)
