from dataclasses import dataclass
from uuid import UUID


@dataclass
class NotifyGroupOwnerPromotedCommand:
    group_id: UUID
    user_id: UUID
    added_by_user_id: UUID
