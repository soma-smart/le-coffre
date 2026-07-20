from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt

from identity_access_management_context.application.gateways import Token, TokenGateway

ACCESS_TOKEN_TYPE = "access"  # noqa: S105
REFRESH_TOKEN_TYPE = "refresh"  # noqa: S105


class JwtTokenGateway(TokenGateway):
    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_token_expiration_seconds: int,
        refresh_token_expiration_seconds: int,
    ):
        self._secret_key = secret_key
        self._algorithm = algorithm
        self.access_token_expiration_seconds = access_token_expiration_seconds
        self._refresh_token_expiration_seconds = refresh_token_expiration_seconds

    def generate_token(
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
        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=self.access_token_expiration_seconds)
        jti = str(uuid4())

        payload = {
            "user_id": user_id_str,
            "email": email,
            "roles": roles,
            "jti": jti,
            "exp": expires_at,
            "iat": issued_at,
            **claims,
        }

        token_value = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

        return Token(
            value=token_value,
            user_id=user_id,
            email=email,
            roles=roles,
            claims=claims,
            jti=jti,
            issued_at=issued_at,
            expires_at=expires_at,
            token_type=ACCESS_TOKEN_TYPE,
        )

    def generate_refresh_token(
        self,
        user_id: UUID,
        email: str,
        roles: list[str],
    ) -> Token:
        user_id_str = str(user_id)
        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=self._refresh_token_expiration_seconds)
        jti = str(uuid4())

        payload = {
            "user_id": user_id_str,
            "email": email,
            "roles": roles,
            "type": REFRESH_TOKEN_TYPE,
            "jti": jti,
            "exp": expires_at,
            "iat": issued_at,
        }

        refresh_token_value = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        return Token(
            value=refresh_token_value,
            user_id=user_id,
            email=email,
            roles=roles,
            claims={},
            jti=jti,
            issued_at=issued_at,
            expires_at=expires_at,
            token_type=REFRESH_TOKEN_TYPE,
        )

    def validate_token(self, token: str) -> Token | None:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])

            # Access-token validation must reject refresh tokens.
            if payload.get("type") == REFRESH_TOKEN_TYPE:
                return None

            return self._build_token_from_payload(token, payload, token_type=ACCESS_TOKEN_TYPE)

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def validate_refresh_token(self, refresh_token: str) -> Token | None:
        try:
            payload = jwt.decode(refresh_token, self._secret_key, algorithms=[self._algorithm])

            # Check if it's a refresh token
            if payload.get("type") != REFRESH_TOKEN_TYPE:
                return None

            return self._build_token_from_payload(refresh_token, payload, token_type=REFRESH_TOKEN_TYPE)

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def _build_token_from_payload(self, token_value: str, payload: dict[str, Any], token_type: str) -> Token:
        user_id = UUID(payload.get("user_id"))

        standard_fields = {"user_id", "email", "roles", "exp", "iat", "jti", "type"}
        claims = {k: v for k, v in payload.items() if k not in standard_fields}

        return Token(
            value=token_value,
            user_id=user_id,
            email=payload.get("email", ""),
            roles=payload.get("roles", []),
            claims=claims,
            jti=payload.get("jti"),
            issued_at=self._to_datetime(payload.get("iat")),
            expires_at=self._to_datetime(payload.get("exp")),
            token_type=token_type,
        )

    def _to_datetime(self, raw_value: Any) -> datetime | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, datetime):
            return raw_value if raw_value.tzinfo is not None else raw_value.replace(tzinfo=UTC)
        if isinstance(raw_value, (int, float)):
            return datetime.fromtimestamp(raw_value, tz=UTC)
        return None
