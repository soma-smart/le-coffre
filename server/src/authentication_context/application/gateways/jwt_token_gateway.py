from typing import Dict, Any, Protocol


class JWTTokenGateway(Protocol):
    async def generate_token(self, user_id: str, claims: Dict[str, Any]) -> str: ...

    async def validate_token(self, token: str) -> Dict[str, Any]: ...
