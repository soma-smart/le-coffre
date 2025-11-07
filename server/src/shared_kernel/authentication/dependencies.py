from fastapi import Depends, HTTPException, Header, Cookie
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
    SessionRepository,
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


def get_validate_token_usecase(request: Request) -> ValidateUserTokenUseCase:
    user_password_repository: UserPasswordRepository = (
        request.app.state.user_password_repository
    )
    token_gateway: TokenGateway = request.app.state.token_gateway
    session_repository: SessionRepository = request.app.state.session_repository
    sso_user_repository: SsoUserRepository = request.app.state.sso_user_repository

    return ValidateUserTokenUseCase(
        user_password_repository,
        token_gateway,
        session_repository,
        sso_user_repository,
    )


async def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer token"),
    access_token: Optional[str] = Cookie(None, description="JWT token from cookie"),
    validate_usecase: ValidateUserTokenUseCase = Depends(get_validate_token_usecase),
) -> ValidatedUser:
    """
    Validates the JWT token and returns the current user information.

    Priority order for token extraction:
    1. Cookie (access_token) - recommended method
    2. Authorization header (Bearer token) - fallback for backward compatibility

    Raises HTTPException with 401 status for invalid tokens.
    """
    try:
        token = None

        # Try to get token from cookie first (recommended)
        if access_token:
            token = access_token
        # Fallback to Authorization header for backward compatibility
        elif authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]

        if not token:
            raise MissingTokenError("No authentication token provided")

        command = ValidateUserTokenCommand(jwt_token=token)
        response = await validate_usecase.execute(command)

        return ValidatedUser(
            user_id=response.user_id,
            email=response.email,
            display_name=response.display_name,
            session_id=response.session_id,
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
