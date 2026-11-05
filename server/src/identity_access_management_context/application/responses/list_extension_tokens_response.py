from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ExtensionTokenSummary:
    id: UUID
    device_name: str | None
    expires_at: datetime | None
    last_used_at: datetime | None
    is_active: bool


@dataclass
class ListExtensionTokensResponse:
    tokens: list[ExtensionTokenSummary]
