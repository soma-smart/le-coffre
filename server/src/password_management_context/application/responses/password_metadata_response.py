from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PasswordMetadataResponse:
    id: UUID
    name: str
    folder: str
    group_id: UUID  # The owning group ID
