from dataclasses import dataclass
from uuid import UUID

from password_management_context.domain.value_objects import PasswordPermission


@dataclass
class UserAccessResponse:
    user_id: UUID
    permissions: set[PasswordPermission]
    is_owner: bool


@dataclass
class GroupAccessResponse:
    group_id: UUID
    permissions: set[PasswordPermission]
    is_owner: bool


@dataclass
class ListAccessResponse:
    user_accesses: list[UserAccessResponse]
    group_accesses: list[GroupAccessResponse]
