from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass
class Token:
    value: str
    user_id: UUID
    email: str
    roles: list[str]
    claims: dict[str, Any]

    def has_role(self, role: str) -> bool:
        return role in self.roles


class TokenGateway(Protocol):
    async def generate_token(
        self,
        user_id: UUID,
        email: str,
        roles: list[str],
        claims: dict[str, Any] | None = None,
    ) -> Token: ...

    async def generate_refresh_token(
        self,
        user_id: UUID,
        email: str,
        roles: list[str],
    ) -> str: ...

    async def validate_token(self, token: str) -> Token | None: ...

    async def validate_refresh_token(self, refresh_token: str) -> Token | None: ...
