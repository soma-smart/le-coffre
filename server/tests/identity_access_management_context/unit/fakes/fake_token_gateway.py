from datetime import UTC, datetime
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
        jti: str | None = None,
    ) -> None:
        if claims is None:
            claims = {}
        token_obj = Token(
            value=token,
            user_id=user_id,
            email=email,
            roles=roles,
            claims=claims,
            jti=jti,
            token_type="access",
        )
        self.generated_tokens[token] = token_obj

    def generate_token(
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
        issued_at = datetime.now(UTC)
        token_obj = Token(
            value=token_str,
            user_id=user_id,
            email=email,
            roles=roles,
            claims={"user_id": str(user_id), "email": email, "roles": roles, **claims},
            jti=f"access-token-jti-{self.unique_part}",
            issued_at=issued_at,
            token_type="access",
        )
        self.generated_tokens[token_str] = token_obj
        self.last_generated_token = token_obj
        return token_obj

    def generate_refresh_token(
        self,
        user_id: UUID,
        email: str,
        roles: List[str],
    ) -> Token:
        refresh_token_str = f"refresh_token_for_{user_id}_{self.unique_part}"
        return Token(
            value=refresh_token_str,
            user_id=user_id,
            email=email,
            roles=roles,
            claims={"user_id": str(user_id), "email": email, "roles": roles},
            jti=f"refresh-token-jti-{self.unique_part}",
            issued_at=datetime.now(UTC),
            token_type="refresh",
        )

    def validate_token(self, token: str) -> Token | None:
        return self.generated_tokens.get(token)

    def set_valid_refresh_token(
        self,
        refresh_token: str,
        user_id: UUID,
        email: str,
        roles: List[str],
        jti: str | None = None,
    ) -> None:
        token_obj = Token(
            value=refresh_token,
            user_id=user_id,
            email=email,
            roles=roles,
            claims={"user_id": str(user_id), "email": email, "roles": roles},
            jti=jti,
            issued_at=datetime.now(UTC),
            token_type="refresh",
        )
        self.valid_refresh_tokens[refresh_token] = token_obj

    def validate_refresh_token(self, refresh_token: str) -> Token | None:
        return self.valid_refresh_tokens.get(refresh_token)

    def get_last_generated_token(self) -> Token | None:
        return self.last_generated_token
