from typing import Dict, Any, List, Optional
from uuid import UUID
import jwt
from datetime import datetime, timedelta, UTC

from authentication_context.application.gateways import TokenGateway, Token


class JwtTokenGateway(TokenGateway):
    def __init__(self, secret_key: str = "your-secret-key", algorithm: str = "HS256"):
        self._secret_key = secret_key
        self._algorithm = algorithm

    async def generate_token(
        self,
        user_id: UUID,
        email: str,
        roles: List[str],
        claims: Dict[str, Any] | None = None,
    ) -> Token:
        if claims is None:
            claims = {}

        # Convert UUID to string for JWT serialization
        user_id_str = str(user_id)

        payload = {
            "user_id": user_id_str,
            "email": email,
            "roles": roles,
            "exp": datetime.now(UTC) + timedelta(hours=24),
            "iat": datetime.now(UTC),
            **claims,
        }

        token_value = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

        return Token(
            value=token_value,
            user_id=user_id,
            email=email,
            roles=roles,
            claims=claims,
        )

    async def validate_token(self, token: str) -> Optional[Token]:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])

            user_id = UUID(payload.get("user_id"))

            # Extract claims (everything except standard fields)
            standard_fields = {"user_id", "email", "roles", "exp", "iat"}
            claims = {k: v for k, v in payload.items() if k not in standard_fields}

            return Token(
                value=token,
                user_id=user_id,
                email=payload.get("email", ""),
                roles=payload.get("roles", []),
                claims=claims,
            )

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
