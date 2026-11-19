from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from password_management_context.domain.value_objects import AccessRole, PasswordPermission


@dataclass
class UserAccessResponse:
    """One access link: a principal reaches the password through a single group.

    A principal that reaches the password through several groups produces several
    links — one per group.
    """

    principal_id: UUID
    group_id: UUID
    role_in_group: AccessRole
    group_role: AccessRole
    permissions: set[PasswordPermission]
    expires_at: datetime | None = None


@dataclass
class GroupAccessResponse:
    group_id: UUID
    role: AccessRole
    permissions: set[PasswordPermission]
    expires_at: datetime | None = None


@dataclass
class ListAccessResponse:
    user_accesses: list[UserAccessResponse]
    group_accesses: list[GroupAccessResponse]
