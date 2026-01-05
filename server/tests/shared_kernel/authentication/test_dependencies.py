import pytest
from uuid import UUID
from unittest.mock import Mock, AsyncMock

from shared_kernel.authentication.dependencies import get_current_user
from identity_access_management_context.application.responses import (
    ValidateUserTokenResponse,
)
from identity_access_management_context.application.use_cases import (
    ValidateUserTokenUseCase,
)


@pytest.mark.asyncio
async def test_get_current_user_should_use_roles_from_token_response():
    # Given a valid JWT token with ["user"] role in cookie
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "sso_user@lecoffre.com"
    display_name = "SSO User"
    jwt_token = "valid_jwt_token_for_sso_user"

    mock_usecase = Mock(spec=ValidateUserTokenUseCase)
    mock_usecase.execute = AsyncMock(
        return_value=ValidateUserTokenResponse(
            is_valid=True,
            user_id=user_id,
            email=email,
            display_name=display_name,
            roles=["user"],
        )
    )

    # When get_current_user() is called with cookie
    validated_user = await get_current_user(
        access_token=jwt_token, validate_usecase=mock_usecase
    )

    # Then ValidatedUser should have roles=["user"]
    assert validated_user.roles == ["user"]
    assert validated_user.user_id == user_id
    assert validated_user.email == email
    assert validated_user.display_name == display_name


@pytest.mark.asyncio
async def test_get_current_user_should_preserve_admin_role_for_admin_users():
    # Given a valid JWT token with ["admin"] role in cookie
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"
    jwt_token = "valid_jwt_token_for_admin"

    mock_usecase = Mock(spec=ValidateUserTokenUseCase)
    mock_usecase.execute = AsyncMock(
        return_value=ValidateUserTokenResponse(
            is_valid=True,
            user_id=user_id,
            email=email,
            display_name=display_name,
            roles=["admin"],
        )
    )

    # When get_current_user() is called with cookie
    validated_user = await get_current_user(
        access_token=jwt_token, validate_usecase=mock_usecase
    )

    # Then ValidatedUser should have roles=["admin"]
    assert validated_user.roles == ["admin"]
    assert validated_user.user_id == user_id
    assert validated_user.email == email
    assert validated_user.display_name == display_name