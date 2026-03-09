from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from identity_access_management_context.application.gateways import Token, TokenGateway


class JwtTokenGateway(TokenGateway):
    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_token_expiration_minutes: int,
        refresh_token_expiration_days: int,
    ):
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expiration_minutes = access_token_expiration_minutes
        self._refresh_token_expiration_days = refresh_token_expiration_days

    async def generate_token(
        self,
        user_id: UUID,
        email: str,
        roles: list[str],
        claims: dict[str, Any] | None = None,
    ) -> Token:
        if claims is None:
            claims = {}

        # Convert UUID to string for JWT serialization
        user_id_str = str(user_id)

        payload = {
            "user_id": user_id_str,
            "email": email,
            "roles": roles,
            "exp": datetime.now(UTC) + timedelta(minutes=self._access_token_expiration_minutes),
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

    async def generate_refresh_token(
        self,
        user_id: UUID,
        email: str,
        roles: list[str],
    ) -> str:
        user_id_str = str(user_id)

        payload = {
            "user_id": user_id_str,
            "email": email,
            "roles": roles,
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(days=self._refresh_token_expiration_days),
            "iat": datetime.now(UTC),
        }

        refresh_token_value = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        return refresh_token_value

    async def validate_token(self, token: str) -> Token | None:
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

    async def validate_refresh_token(self, refresh_token: str) -> Token | None:
        try:
            payload = jwt.decode(refresh_token, self._secret_key, algorithms=[self._algorithm])

            # Check if it's a refresh token
            if payload.get("type") != "refresh":
                return None

            user_id = UUID(payload.get("user_id"))

            # Extract claims (everything except standard fields)
            standard_fields = {"user_id", "email", "roles", "exp", "iat", "type"}
            claims = {k: v for k, v in payload.items() if k not in standard_fields}

            return Token(
                value=refresh_token,
                user_id=user_id,
                email=payload.get("email", ""),
                roles=payload.get("roles", []),
                claims=claims,
            )

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
