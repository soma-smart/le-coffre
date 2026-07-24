from uuid import UUID

from identity_access_management_context.adapters.secondary.jwt_token_gateway import JwtTokenGateway


def build_gateway() -> JwtTokenGateway:
    return JwtTokenGateway(
        secret_key="test-secret-key-which-is-long-enough",
        algorithm="HS256",
        access_token_expiration_seconds=300,
        refresh_token_expiration_seconds=3600,
    )


def test_validate_token_rejects_refresh_token() -> None:
    gateway = build_gateway()
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    refresh_token = gateway.generate_refresh_token(
        user_id=user_id,
        email="user@example.com",
        roles=["user"],
    )

    validated_access_token = gateway.validate_token(refresh_token.value)

    assert validated_access_token is None


def test_validate_token_accepts_access_token() -> None:
    gateway = build_gateway()
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    access_token = gateway.generate_token(
        user_id=user_id,
        email="user@example.com",
        roles=["user"],
    )

    validated_access_token = gateway.validate_token(access_token.value)

    assert validated_access_token is not None
    assert validated_access_token.user_id == user_id


def test_validate_refresh_token_rejects_access_token() -> None:
    gateway = build_gateway()
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    access_token = gateway.generate_token(
        user_id=user_id,
        email="user@example.com",
        roles=["user"],
    )

    validated_refresh_token = gateway.validate_refresh_token(access_token.value)

    assert validated_refresh_token is None
