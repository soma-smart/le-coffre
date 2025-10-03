from typing import Dict, Any, List, Union
from uuid import UUID
from authentication_context.application.gateways import TokenGateway, Token


class FakeTokenGateway(TokenGateway):
    def __init__(self):
        self.generated_tokens = {}
        self.generation_calls = []
        self.unique_part = ""

    def set_unique_jwt_part(self, unique_part: str):
        self.unique_part = unique_part

    def set_valid_token(
        self,
        token: str,
        user_id: Union[UUID, str],
        email: str,
        roles: List[str],
        claims: Dict[str, Any] | None = None,
    ) -> None:
        if claims is None:
            claims = {}
        token_obj = Token(
            value=token, user_id=user_id, email=email, roles=roles, claims=claims
        )
        self.generated_tokens[token] = token_obj

    async def generate_token(
        self,
        user_id: Union[UUID, str],
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
        return token_obj

    async def validate_token(self, token: str) -> Token | None:
        return self.generated_tokens.get(token)
