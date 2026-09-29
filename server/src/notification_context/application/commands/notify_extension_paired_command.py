from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class NotifyExtensionPairedCommand:
    user_id: UUID
    device_name: str
    created_from_ip: str | None
    paired_at: datetime
