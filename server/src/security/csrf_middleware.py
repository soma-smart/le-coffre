"""CSRF protection middleware for FastAPI."""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from identity_access_management_context.adapters.secondary.sql import (
    SqlRevokedTokenRepository,
    SqlSsoUserRepository,
    SqlUserPasswordRepository,
    SqlUserRepository,
)
from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.use_cases import (
    ValidateUserTokenUseCase,
)

logger = logging.getLogger(__name__)


def _sanitize_path(path: str) -> str:
    """Truncate path to at most 3 segments to avoid logging resource IDs (UUIDs)."""
    parts = path.split("/")
    return "/".join(parts[:4])


class CsrfMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware using the Synchronizer Token Pattern.

    Validates CSRF tokens on mutating requests (POST, PUT, DELETE, PATCH).
    Exempt routes are those reached before a CSRF token can exist (login,
    registration, refresh, vault bootstrap/unlock).

    The token must be sent in the 'X-CSRF-Token' header.
    """

    # Routes that are exempt from CSRF protection.
    # Note: SSO routes are deliberately NOT exempt. Its read endpoints (url,
    # callback, is-configured) are GETs and are skipped by the method check
    # anyway, while /api/auth/sso/configure is an authenticated admin POST that
    # must carry a CSRF token — defense in depth on top of SameSite=strict.
    EXEMPT_ROUTES = [
        "/api/auth/refresh-token",
        "/api/auth/login",  # Login generates the token, can't require it
        "/api/auth/register-admin",  # Registration happens before token exists
        "/api/vault/setup",  # Vault setup happens before CSRF token exists
        "/api/vault/validate-setup",  # Validate setup happens immediately after
        "/api/vault/unlock",  # Vault unlock happens before authentication is possible
        # Redeeming a one-time link is anonymous by design: the sole credential is
        # the secret token in the request body, never the session cookie. CSRF
        # protects against a third party spending the caller's ambient authority,
        # and there is none to spend here. Without the exemption a visitor who
        # happens to be logged in would be rejected, since the public page has no
        # CSRF token in its store.
        "/api/one-time-links/consume",
    ]

    # HTTP methods that require CSRF protection
    PROTECTED_METHODS = ["POST", "PUT", "DELETE", "PATCH"]

    async def dispatch(self, request: Request, call_next):
        """Process the request and validate CSRF token if needed."""

        # Skip CSRF check for non-protected methods
        if request.method not in self.PROTECTED_METHODS:
            return await call_next(request)

        # Skip CSRF check for exempt routes
        if self._is_exempt_route(request.url.path):
            return await call_next(request)

        # Skip CSRF check for OpenAPI documentation endpoints
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)

        # Check authentication first - if no auth token, let auth middleware handle it (returns 401)
        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")
        if not access_token and not refresh_token:
            # No authentication, skip CSRF check and let auth middleware return 401
            return await call_next(request)

        # Validate CSRF token (only for authenticated requests)
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            logger.warning(
                "CSRF token missing for %s %s",
                request.method,
                _sanitize_path(request.url.path),
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"},
            )

        try:
            # Get dependencies from app state
            session_maker = request.app.state.session_maker
            csrf_token_manager = request.app.state.csrf_token_manager
            token_gateway = request.app.state.token_gateway
            time_provider = request.app.state.time_provider

            with session_maker() as session:
                user_password_repository = SqlUserPasswordRepository(session)
                user_repository = SqlUserRepository(session)
                revoked_token_repository = SqlRevokedTokenRepository(session)
                sso_user_repository = SqlSsoUserRepository(session)

                validate_usecase = ValidateUserTokenUseCase(
                    user_password_repository,
                    token_gateway,
                    sso_user_repository,
                    user_repository,
                    revoked_token_repository,
                    time_provider,
                )

                if access_token:
                    # Validate access token and derive user ID
                    command = ValidateUserTokenCommand(jwt_token=access_token)
                    response = validate_usecase.execute(command)
                    user_id = response.user_id
                else:
                    # Refresh-only sessions still need CSRF enforcement on mutating routes.
                    #
                    # COUPLING NOTE: this branch re-implements a subset of refresh
                    # validation and deliberately does NOT check AuthSession state.
                    # It is safe only because every invalidation path today either
                    # revokes the token (logout, rotation) or bumps the user's
                    # session_invalid_before cutoff (password update, reuse
                    # containment) — the two things checked below. Any future
                    # invalidation path that only sets AuthSession.invalidated_at
                    # must add an active-session check here.
                    refresh_token_obj = token_gateway.validate_refresh_token(refresh_token)
                    if refresh_token_obj is None:
                        raise ValueError("Invalid refresh token")

                    now = time_provider.get_current_time()
                    if refresh_token_obj.jti and revoked_token_repository.is_revoked(refresh_token_obj.jti, now):
                        raise ValueError("Revoked refresh token")

                    authenticated_user = user_repository.get_by_id(refresh_token_obj.user_id)
                    if authenticated_user is not None and authenticated_user.session_invalid_before is not None:
                        session_cutoff = authenticated_user.session_invalid_before
                        if refresh_token_obj.issued_at is None or refresh_token_obj.issued_at < session_cutoff:
                            raise ValueError("Invalidated refresh token")

                    user_id = refresh_token_obj.user_id

                # Validate CSRF token
                if not csrf_token_manager.validate_token(user_id, csrf_token):
                    logger.warning(
                        "Invalid CSRF token for user %s on %s %s",
                        user_id,
                        request.method,
                        _sanitize_path(request.url.path),
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Invalid or expired CSRF token"},
                    )

        except Exception:
            logger.exception("Error validating CSRF token")
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )

        # CSRF token is valid, proceed with request
        return await call_next(request)

    def _is_exempt_route(self, path: str) -> bool:
        """Check if the route is exempt from CSRF protection."""
        return any(path.startswith(route) for route in self.EXEMPT_ROUTES)
