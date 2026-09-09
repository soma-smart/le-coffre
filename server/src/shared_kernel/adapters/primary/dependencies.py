from typing import Generator

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyCookie
from sqlmodel import Session
from starlette.requests import Request

from config import get_extension_last_used_coarsening_seconds
from identity_access_management_context.adapters.secondary.sql import (
    SqlExtensionTokenRepository,
    SqlRevokedTokenRepository,
    SqlSsoUserRepository,
    SqlUserPasswordRepository,
    SqlUserRepository,
)
from identity_access_management_context.application.commands import (
    ValidateExtensionTokenCommand,
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.gateways import (
    RevokedTokenRepository,
    TokenGateway,
)
from identity_access_management_context.application.use_cases import (
    ValidateExtensionTokenUseCase,
    ValidateUserTokenUseCase,
)
from identity_access_management_context.domain.exceptions import (
    ExtensionDomainError,
    InvalidTokenException,
    SessionNotFoundException,
    UserNotFoundException,
)
from shared_kernel.domain.entities import ApiPrincipal, ValidatedUser
from shared_kernel.domain.exceptions import ReadOnlyCredentialError

from .exceptions import (
    MissingTokenError,
)

# Security scheme for Swagger documentation
cookie_scheme = APIKeyCookie(name="access_token", scheme_name="CookieAuth", auto_error=False)

# Browser extensions only. Cookie auth cannot work from a chrome-extension://
# origin: every session cookie is SameSite=strict, so the browser never
# attaches it to a request initiated there.
bearer_scheme = HTTPBearer(scheme_name="ExtensionBearer", auto_error=False)

# The only role an extension principal ever carries. Never the user's own:
# ListPasswordsUseCase hands an admin every password on the instance (metadata
# only, but that is still every name, login and URL), and that list would end
# up sitting in a browser profile.
EXTENSION_PRINCIPAL_ROLE = "user"


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
    user_repository = SqlUserRepository(session)
    revoked_token_repository: RevokedTokenRepository = SqlRevokedTokenRepository(session)
    token_gateway: TokenGateway = request.app.state.token_gateway
    sso_user_repository = SqlSsoUserRepository(session)
    time_provider = request.app.state.time_provider

    return ValidateUserTokenUseCase(
        user_password_repository,
        token_gateway,
        sso_user_repository,
        user_repository,
        revoked_token_repository,
        time_provider,
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


def get_validate_extension_token_usecase(
    request: Request,
    session: Session = Depends(get_session),
) -> ValidateExtensionTokenUseCase:
    return ValidateExtensionTokenUseCase(
        SqlExtensionTokenRepository(session),
        SqlUserPasswordRepository(session),
        SqlSsoUserRepository(session),
        SqlUserRepository(session),
        request.app.state.time_provider,
        get_extension_last_used_coarsening_seconds(),
    )


def get_current_principal(
    request: Request,
    access_token: str | None = Depends(cookie_scheme),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    validate_usecase: ValidateUserTokenUseCase = Depends(get_validate_token_usecase),
    validate_extension_usecase: ValidateExtensionTokenUseCase = Depends(get_validate_extension_token_usecase),
) -> ApiPrincipal:
    """Resolve the caller, by cookie or by extension bearer token.

    Opt-in: only the handful of read routes an extension needs declare this.
    `get_current_user` is untouched, so the ~40 routes on it cannot become
    bearer-reachable by accident. That matters more than it looks: several of
    them are GETs (`/users`, `/admin/one-time-links`, `/passwords/statistics`),
    so a blanket bearer path guarded only by HTTP method would have exposed them.

    Three rules, in order:

    1. A cookie wins, and a bad cookie is fatal. Never fall through to the
       bearer: that would let an attacker-supplied token rescue an expired
       cookie, and it would break the SPA's 401-then-refresh flow.
    2. Otherwise a bearer resolves to an extension principal, with the user's
       roles replaced by a plain non-admin role. An admin's own roles would make
       `/passwords/list` return the names, logins and URLs of every secret on
       the instance, into a browser profile.
    3. Otherwise 401.
    """
    if access_token:
        principal = ApiPrincipal.session(_validate_session(access_token, validate_usecase))
    elif credentials is not None and credentials.credentials:
        principal = ApiPrincipal.extension(_validate_extension(credentials.credentials, validate_extension_usecase))
    else:
        raise HTTPException(status_code=401, detail="No authentication token provided")

    try:
        principal.ensure_method_allowed(request.method)
    except ReadOnlyCredentialError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    return principal


def _validate_session(
    access_token: str,
    validate_usecase: ValidateUserTokenUseCase,
) -> ValidatedUser:
    try:
        response = validate_usecase.execute(ValidateUserTokenCommand(jwt_token=access_token))
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
    ) as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service error") from e


def _validate_extension(
    raw_token: str,
    validate_extension_usecase: ValidateExtensionTokenUseCase,
) -> ValidatedUser:
    try:
        response = validate_extension_usecase.execute(ValidateExtensionTokenCommand(raw_token=raw_token))
    except ExtensionDomainError as e:
        # One generic 401 for unknown, expired, revoked and cutoff alike, so a
        # token holder cannot tell which happened. The distinct exception types
        # exist only so the server can log it.
        raise HTTPException(status_code=401, detail="Invalid extension token") from e
    except UserNotFoundException as e:
        raise HTTPException(status_code=401, detail="Invalid extension token") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service error") from e

    # Roles are NOT echoed from the user. See get_current_principal.
    return ValidatedUser(
        user_id=response.user_id,
        email=response.email,
        display_name=response.display_name,
        roles=[EXTENSION_PRINCIPAL_ROLE],
    )
