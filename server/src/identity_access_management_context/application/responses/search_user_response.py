from dataclasses import dataclass
from uuid import UUID


@dataclass
class SearchUserResponse:
    id: UUID
    username: str
    name: str
