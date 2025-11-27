from dataclasses import dataclass
from uuid import UUID


@dataclass
class RefreshAccessTokenResponse:
    access_token: str
    user_id: UUID
