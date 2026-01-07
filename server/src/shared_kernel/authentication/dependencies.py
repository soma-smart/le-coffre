from fastapi import Depends, HTTPException
from fastapi.security.api_key import APIKeyCookie
from typing import Optional
from starlette.requests import Request

from identity_access_management_context.application.use_cases import (
    ValidateUserTokenUseCase,
)
from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    TokenGateway,
    SsoUserRepository,
)
from identity_access_management_context.domain.exceptions import (
    InvalidTokenException,
    SessionNotFoundException,
    UserNotFoundException,
)
from .models import ValidatedUser
from .exceptions import (
    MissingTokenError,
)


# Security scheme for Swagger documentation
cookie_scheme = APIKeyCookie(
    name="access_token", scheme_name="CookieAuth", auto_error=False
)


def get_validate_token_usecase(request: Request) -> ValidateUserTokenUseCase:
    user_password_repository: UserPasswordRepository = (
        request.app.state.user_password_repository
    )
    token_gateway: TokenGateway = request.app.state.token_gateway
    sso_user_repository: SsoUserRepository = request.app.state.sso_user_repository

    return ValidateUserTokenUseCase(
        user_password_repository,
        token_gateway,
        sso_user_repository,
    )


async def get_current_user(
    access_token: Optional[str] = Depends(cookie_scheme),
    validate_usecase: ValidateUserTokenUseCase = Depends(get_validate_token_usecase),
) -> ValidatedUser:
    """
    Validates the JWT token from cookie and returns the current user information.

    Expects the JWT token in the 'access_token' cookie.
    Raises HTTPException with 401 status for invalid or missing tokens.
    """
    try:
        if not access_token:
            raise MissingTokenError("No authentication token provided")

        command = ValidateUserTokenCommand(jwt_token=access_token)
        response = await validate_usecase.execute(command)

        return ValidatedUser(
            user_id=response.user_id,
            email=response.email,
            display_name=response.display_name,
            roles=response.roles,
        )

    except (
        InvalidTokenException,
        SessionNotFoundException,
        UserNotFoundException,
        MissingTokenError,
    ) as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Authentication service error")
