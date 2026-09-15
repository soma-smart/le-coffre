from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ExtensionTokenSummary:
    id: UUID
    device_name: str
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_from_ip: str | None
    is_active: bool


@dataclass
class ListExtensionTokensResponse:
    tokens: list[ExtensionTokenSummary]
