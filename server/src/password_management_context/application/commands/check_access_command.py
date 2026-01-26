from dataclasses import dataclass
from uuid import UUID
from password_management_context.domain.value_objects import PasswordPermission


@dataclass
class CheckAccessCommand:
    user_id: UUID
    resource_id: UUID
    permission: PasswordPermission = PasswordPermission.READ
