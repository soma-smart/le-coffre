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
    SsoUserRepository,
)
from identity_access_management_context.domain.exceptions import (
    InvalidTokenException,
    UserNotFoundException,
)
from shared_kernel.domain import AuthenticatedUser
from .exceptions import MissingTokenError


def get_validate_token_usecase(request: Request) -> ValidateUserTokenUseCase:
    """
    Creates ValidateUserTokenUseCase with dependencies from app state.

    This function extracts the necessary repositories and gateways from the
    FastAPI app state to instantiate the use case.
    """
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
    authorization: str = Header(..., description="Bearer token"),
    validate_usecase: ValidateUserTokenUseCase = Depends(get_validate_token_usecase),
) -> AuthenticatedUser:
    """
    FastAPI dependency that validates JWT token and returns authenticated user.

    This dependency is used across all contexts to authenticate users
    from HTTP requests.

    Args:
        authorization: Bearer token from HTTP Authorization header
        validate_usecase: Use case for validating tokens (injected)

    Returns:
        AuthenticatedUser with user_id and roles

    Raises:
        HTTPException: 401 for authentication failures, 500 for server errors
    """
    try:
        if not authorization.startswith("Bearer "):
            raise MissingTokenError("Invalid authorization header format")

        token = authorization.split(" ")[1]

        command = ValidateUserTokenCommand(jwt_token=token)
        response = await validate_usecase.execute(command)

        return AuthenticatedUser(
            user_id=response.user_id,
            roles=response.roles,
        )

    except (
        InvalidTokenException,
        UserNotFoundException,
        MissingTokenError,
    ) as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service error")
