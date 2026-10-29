from dataclasses import dataclass
from typing import Generator

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyCookie, APIKeyHeader
from fastapi.security.utils import get_authorization_scheme_param
from sqlmodel import Session
from starlette.requests import Request

from config import get_extension_last_used_coarsening_seconds
from identity_access_management_context.adapters.secondary.sql import (
    SqlIamEventRepository,
    SQLPrincipalRepository,
    SqlRevokedTokenRepository,
    SqlServiceAccountRepository,
    SqlTokenCredentialRecordRepository,
    SqlUserRepository,
)
from identity_access_management_context.application.commands import (
    AuthenticateTokenCommand,
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.gateways import (
    RevokedTokenRepository,
    TokenGateway,
)
from identity_access_management_context.application.services.authentication import TokenAuthenticator
from identity_access_management_context.application.use_cases import (
    AuthenticateTokenUseCase,
    ValidateUserTokenUseCase,
)
from identity_access_management_context.domain.exceptions import (
    InvalidTokenException,
    SessionNotFoundException,
    UserNotFoundException,
)
from shared_kernel.domain.entities import (
    AuthenticatedPrincipal,
    AuthenticatedUser,
    PresentedCredential,
    ValidatedUser,
)
from shared_kernel.domain.exceptions import CredentialAuthenticationError

from .exceptions import (
    MissingTokenError,
)

# Security schemes for Swagger documentation
cookie_scheme = APIKeyCookie(name="access_token", scheme_name="CookieAuth", auto_error=False)
csrf_scheme = APIKeyHeader(name="X-CSRF-Token", scheme_name="CsrfToken", auto_error=False)

# Token credentials, for callers that cannot hold a session: a browser extension
# cannot send cookies from a chrome-extension:// origin, as every session cookie
# is SameSite=strict.
bearer_scheme = HTTPBearer(scheme_name="BearerAuth", auto_error=False)


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
    user_repository = SqlUserRepository(session)
    revoked_token_repository: RevokedTokenRepository = SqlRevokedTokenRepository(session)
    token_gateway: TokenGateway = request.app.state.token_gateway
    time_provider = request.app.state.time_provider

    return ValidateUserTokenUseCase(
        token_gateway,
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


def get_client_ip(request: Request) -> str:
    """The caller's IP, trusting X-Forwarded-For exactly as far as the rate limiter does."""
    # Imported here: the `security` package imports this module for its own routes.
    from security.client_ip import resolve_client_ip

    return resolve_client_ip(
        request,
        trusted_proxies=request.app.state.rate_limit_trusted_proxies,
        hops=request.app.state.rate_limit_trusted_proxy_hops,
    )


def get_authenticate_token_usecase(
    request: Request,
    session: Session = Depends(get_session),
) -> AuthenticateTokenUseCase:
    token_credential_record_repository = SqlTokenCredentialRecordRepository(session)
    principal_repository = SQLPrincipalRepository(
        session, SqlUserRepository(session), SqlServiceAccountRepository(session)
    )
    return AuthenticateTokenUseCase(
        TokenAuthenticator(
            principal_repository=principal_repository,
            token_credential_record_repository=token_credential_record_repository,
            time_provider=request.app.state.time_provider,
        ),
        token_credential_record_repository,
        request.app.state.domain_event_publisher,
        SqlIamEventRepository(session),
        request.app.state.time_provider,
        get_extension_last_used_coarsening_seconds(),
    )


# Methods a read-only credential may use. Everything else is refused before the
# route body runs.
READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class _Authentication:
    """Everything one request proved, resolved once and shared by the dependencies below."""

    principal: AuthenticatedPrincipal
    roles: list[str]
    credential: PresentedCredential | None


def _authenticate(
    request: Request,
    access_token: str | None = Depends(cookie_scheme),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    client_ip: str = Depends(get_client_ip),
    validate_usecase: ValidateUserTokenUseCase = Depends(get_validate_token_usecase),
    authenticate_token_usecase: AuthenticateTokenUseCase = Depends(get_authenticate_token_usecase),
) -> _Authentication:
    """Resolve the caller, by session cookie or by token.

    Three rules, in order:

    1. A cookie wins, and a bad cookie is fatal. Never fall through to the
       token: that would let an attacker-supplied token rescue an expired
       cookie, and it would break the SPA's 401-then-refresh flow.
    2. Otherwise a bearer token is authenticated, whatever principal it proves.
       A read-only one may only read, and never with admin privileges: an
       admin's own roles would make `/passwords/list` return the names, logins
       and URLs of every secret on the instance, into a browser profile.
    3. Otherwise 401.
    """
    if access_token:
        user = _validate_session(access_token, validate_usecase)
        return _Authentication(
            principal=AuthenticatedPrincipal(principal_id=user.user_id, kind="user"),
            roles=user.roles,
            credential=None,
        )

    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="No authentication token provided")

    try:
        response = authenticate_token_usecase.execute(
            AuthenticateTokenCommand(token=credentials.credentials, client_ip=client_ip)
        )
    except CredentialAuthenticationError as e:
        # One generic 401 for malformed, unknown, expired and idle alike, so a
        # token holder cannot tell which happened.
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"}) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service error") from e

    if response.read_only and request.method.upper() not in READ_ONLY_METHODS:
        raise HTTPException(status_code=403, detail="This credential is read-only")

    return _Authentication(
        principal=AuthenticatedPrincipal(principal_id=response.principal_id, kind=response.principal_kind),
        roles=[] if response.read_only else response.roles,
        credential=PresentedCredential(credential_id=response.credential_id, read_only=response.read_only),
    )


def get_current_principal(authentication: _Authentication = Depends(_authenticate)) -> AuthenticatedPrincipal:
    """Who is calling, by session or by token.

    Opt-in: only the routes a token may reach declare it, or a dependency built
    on it. `get_current_user` never reads a token, so the routes on it cannot
    become token-reachable by accident.
    """
    return authentication.principal


def get_current_credential(
    authentication: _Authentication = Depends(_authenticate),
) -> PresentedCredential | None:
    """The stored credential the caller authenticated with, if not a session."""
    return authentication.credential


def get_current_requesting_user(authentication: _Authentication = Depends(_authenticate)) -> AuthenticatedUser:
    """The calling user, with the roles this request may use: none through a read-only credential."""
    if authentication.principal.kind != "user":
        raise HTTPException(status_code=403, detail="Only a user may call this route")
    return AuthenticatedUser(user_id=authentication.principal.principal_id, roles=authentication.roles)


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


def _read_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization is None:
        return None
    scheme, token = get_authorization_scheme_param(authorization)
    # A header that is not a Bearer one is a malformed token, not a missing one.
    return token if scheme.lower() == "bearer" else ""


def get_current_service_account(
    request: Request,
    # Read from the raw header below, declared for the OpenAPI security scheme only:
    # HTTPBearer folds a missing and a malformed header into the same `None`.
    _bearer: object = Security(bearer_scheme),
    client_ip: str = Depends(get_client_ip),
    authenticate_token_usecase: AuthenticateTokenUseCase = Depends(get_authenticate_token_usecase),
) -> AuthenticatedPrincipal:
    """The service account calling, from its token in the 'Authorization: Bearer' header.

    Never reads the cookie: a route depending on this is a machine-only route.
    Every failure gets the same 401, so probing cannot tell why a token was refused.
    """
    try:
        response = authenticate_token_usecase.execute(
            AuthenticateTokenCommand(
                token=_read_bearer_token(request), client_ip=client_ip, required_kind="service_account"
            )
        )
    except CredentialAuthenticationError as e:
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"}) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service error") from e
    return AuthenticatedPrincipal(principal_id=response.principal_id, kind=response.principal_kind)
