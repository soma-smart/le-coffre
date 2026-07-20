from dataclasses import dataclass
from uuid import UUID


@dataclass
class RevokeOneTimeLinkCommand:
    link_id: UUID
    requesting_user_id: UUID
