from dataclasses import dataclass
from uuid import UUID


@dataclass
class DeletePasswordsForDeletedUserCommand:
    personal_group_id: UUID
    deleted_by_user_id: UUID
