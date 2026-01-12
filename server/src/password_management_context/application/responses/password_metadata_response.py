from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PasswordMetadataResponse:
    id: UUID
    name: str
    folder: str
