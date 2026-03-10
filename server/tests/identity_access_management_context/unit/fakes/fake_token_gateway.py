from typing import Any, Dict, List
from uuid import UUID

from identity_access_management_context.application.gateways import Token, TokenGateway


class FakeTokenGateway(TokenGateway):
    def __init__(self):
        self.generated_tokens = {}
        self.generation_calls = []
        self.unique_part = ""
        self.valid_refresh_tokens = {}
        self.last_generated_token = None

    def set_unique_jwt_part(self, unique_part: str):
        self.unique_part = unique_part

    def set_valid_token(
        self,
        token: str,
        user_id: UUID,
        email: str,
        roles: List[str],
        claims: Dict[str, Any] | None = None,
    ) -> None:
        if claims is None:
            claims = {}
        token_obj = Token(value=token, user_id=user_id, email=email, roles=roles, claims=claims)
        self.generated_tokens[token] = token_obj

    async def generate_token(
        self,
        user_id: UUID,
        email: str,
        roles: List[str],
        claims: Dict[str, Any] | None = None,
    ) -> Token:
        if claims is None:
            claims = {}
        self.generation_calls.append((user_id, email, roles, claims))
        # Use user_id for the token string to maintain consistency
        token_str = f"jwt_token_for_{user_id}_{self.unique_part}"
        token_obj = Token(
            value=token_str,
            user_id=user_id,
            email=email,
            roles=roles,
            claims={"user_id": str(user_id), "email": email, "roles": roles, **claims},
        )
        self.generated_tokens[token_str] = token_obj
        self.last_generated_token = token_obj
        return token_obj

    async def generate_refresh_token(
        self,
        user_id: UUID,
        email: str,
        roles: List[str],
    ) -> str:
        refresh_token_str = f"refresh_token_for_{user_id}_{self.unique_part}"
        return refresh_token_str

    async def validate_token(self, token: str) -> Token | None:
        return self.generated_tokens.get(token)

    def set_valid_refresh_token(
        self,
        refresh_token: str,
        user_id: UUID,
        email: str,
        roles: List[str],
    ) -> None:
        token_obj = Token(
            value=refresh_token,
            user_id=user_id,
            email=email,
            roles=roles,
            claims={"user_id": str(user_id), "email": email, "roles": roles},
        )
        self.valid_refresh_tokens[refresh_token] = token_obj

    async def validate_refresh_token(self, refresh_token: str) -> Token | None:
        return self.valid_refresh_tokens.get(refresh_token)

    def get_last_generated_token(self) -> Token | None:
        return self.last_generated_token
