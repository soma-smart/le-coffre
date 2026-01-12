from dataclasses import dataclass
from uuid import UUID

from password_management_context.domain.value_objects import PasswordPermission


@dataclass
class AccessResponse:
    user_id: UUID
    permissions: set[PasswordPermission]


@dataclass
class ListAccessResponse:
    accesses: list[AccessResponse]
