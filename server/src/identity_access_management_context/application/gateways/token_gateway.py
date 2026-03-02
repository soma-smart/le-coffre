from typing import Dict, Any, Protocol, List, Optional
from dataclasses import dataclass
from uuid import UUID


@dataclass
class Token:
    value: str
    user_id: UUID
    email: str
    roles: List[str]
    claims: Dict[str, Any]

    def has_role(self, role: str) -> bool:
        return role in self.roles


class TokenGateway(Protocol):
    async def generate_token(
        self,
        user_id: UUID,
        email: str,
        roles: List[str],
        claims: Dict[str, Any] | None = None,
    ) -> Token: ...

    async def generate_refresh_token(
        self,
        user_id: UUID,
        email: str,
        roles: List[str],
    ) -> str: ...

    async def validate_token(self, token: str) -> Optional[Token]: ...

    async def validate_refresh_token(self, refresh_token: str) -> Optional[Token]: ...

    async def revoke_refresh_token(self, refresh_token: str) -> None: ...
