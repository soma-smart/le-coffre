from typing import Generator

from fastapi import Depends, HTTPException
from fastapi.security.api_key import APIKeyCookie
from sqlmodel import Session
from starlette.requests import Request

from identity_access_management_context.adapters.secondary.sql import (
    SqlSsoUserRepository,
    SqlUserPasswordRepository,
)
from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.gateways import (
    TokenGateway,
)
from identity_access_management_context.application.use_cases import (
    ValidateUserTokenUseCase,
)
from identity_access_management_context.domain.exceptions import (
    InvalidTokenException,
    SessionNotFoundException,
    UserNotFoundException,
)
from shared_kernel.domain.entities import ValidatedUser

from .exceptions import (
    MissingTokenError,
)

# Security scheme for Swagger documentation
cookie_scheme = APIKeyCookie(name="access_token", scheme_name="CookieAuth", auto_error=False)


def get_session(request: Request) -> Generator[Session, None, None]:
    """
    Dependency that provides a database session for each request.
    Creates a new session from the session maker stored in app.state.
    """
    session_maker = request.app.state.session_maker
    with session_maker() as session:
        yield session


def get_validate_token_usecase(
    request: Request,
    session: Session = Depends(get_session),
) -> ValidateUserTokenUseCase:
    user_password_repository = SqlUserPasswordRepository(session)
    token_gateway: TokenGateway = request.app.state.token_gateway
    sso_user_repository = SqlSsoUserRepository(session)

    return ValidateUserTokenUseCase(
        user_password_repository,
        token_gateway,
        sso_user_repository,
    )


def get_current_user(
    access_token: str | None = Depends(cookie_scheme),
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
        response = validate_usecase.execute(command)

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
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service error") from e
