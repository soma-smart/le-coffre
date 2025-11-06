from fastapi import Depends, HTTPException, Header
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
from .constants import ADMIN_ROLE


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
    authorization: str = Header(..., description="Bearer token"),
    validate_usecase: ValidateUserTokenUseCase = Depends(get_validate_token_usecase),
) -> ValidatedUser:
    """
    Validates the JWT token and returns the current user information.

    Raises HTTPException with 401 status for invalid tokens.
    """
    try:
        if not authorization.startswith("Bearer "):
            raise MissingTokenError("Invalid authorization header format")

        token = authorization.split(" ")[1]

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
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service error")
