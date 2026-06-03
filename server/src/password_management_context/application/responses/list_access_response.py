from dataclasses import dataclass
from uuid import UUID

from password_management_context.domain.value_objects import AccessRole, PasswordPermission


@dataclass
class UserAccessResponse:
    """One access link: a user reaches the password through a single group.

    A user who reaches the password through several groups produces several
    links — one per group.
    """

    user_id: UUID
    group_id: UUID
    role_in_group: AccessRole
    group_role: AccessRole
    permissions: set[PasswordPermission]


@dataclass
class GroupAccessResponse:
    group_id: UUID
    role: AccessRole
    permissions: set[PasswordPermission]


@dataclass
class ListAccessResponse:
    user_accesses: list[UserAccessResponse]
    group_accesses: list[GroupAccessResponse]
