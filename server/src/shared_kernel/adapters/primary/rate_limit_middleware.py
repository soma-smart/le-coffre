"""Rate limiting middleware for FastAPI.

Two mutually exclusive "principal" buckets govern all non-exempt /api traffic:

  * ``user:<id>:api``  — for requests with a valid access_token cookie.
  * ``ip:<ip>:api``    — for unauthenticated requests.

In addition, credential-accepting auth routes consume a loose per-IP
"auth-route volume floor" (``ip:<ip>:auth``) regardless of authentication
state.  This floor is pure DoS protection; brute-force defense lives in the
InMemoryLoginLockoutGateway service, not here.

Principal resolution (who is this caller?) is delegated to a
:class:`PrincipalResolver` stashed on ``app.state.principal_resolver`` so this
middleware does not need to import IAM-specific token machinery directly.

See docs/superpowers/specs/2026-04-21-rate-limiter-design.md for the full
design rationale, including the XFF trust fix (§3.4).

On a 2xx response the ``X-RateLimit-*`` headers reflect the principal bucket
(per-user or unauthenticated-IP).  On a 429 the headers reflect whichever
bucket rejected the request: the auth-route floor on auth-route rejections,
the principal bucket otherwise.  Clients that compute backoff from ``Limit``
should expect this difference between endpoint classes.
"""

from __future__ import annotations

import logging

from fastapi import Request
from shared_kernel.adapters.primary.client_ip import resolve_client_ip
from shared_kernel.adapters.secondary.in_memory_rate_limiter import (
    InMemoryRateLimiter,
    RateLimitResult,
)
from shared_kernel.application.gateways import PrincipalResolver
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """See module docstring."""

    # Exact-match credential-accepting auth routes.  Read-only SSO helpers
    # (/sso/url, /sso/is-configured, /sso/configure) are intentionally NOT
    # here — they fall through to the regular principal bucket.
    AUTH_ROUTES: tuple[str, ...] = (
        "/api/auth/login",
        "/api/auth/register-admin",
        "/api/auth/refresh-token",
        "/api/auth/sso/callback",
    )

    EXEMPT_PREFIXES: tuple[str, ...] = (
        "/api/health",
        "/docs",
        "/openapi",
    )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if self._is_exempt(path):
            return await call_next(request)

        if not path.startswith("/api"):
            return await call_next(request)

        rate_limiter: InMemoryRateLimiter = request.app.state.rate_limiter
        user_max = request.app.state.rate_limit_user_max_requests
        unauth_max = request.app.state.rate_limit_unauth_max_requests
        auth_max = request.app.state.rate_limit_auth_max_requests
        window = request.app.state.rate_limit_window_seconds
        trusted_proxies = request.app.state.rate_limit_trusted_proxies
        proxy_hops = request.app.state.rate_limit_trusted_proxy_hops

        client_ip = resolve_client_ip(request, trusted_proxies=trusted_proxies, hops=proxy_hops)
        is_auth_route = path in self.AUTH_ROUTES

        # Auth-route volume floor (first check, fails fast before any bucket state is touched).
        # This runs before principal resolution so a flood on /api/auth/login doesn't pay the
        # JWT-decode cost on every rejected request.
        if is_auth_route:
            auth_key = f"ip:{client_ip}:auth"
            auth_result = rate_limiter.check(auth_key, auth_max, window)
            if auth_result.is_limited:
                logger.warning(
                    "Rate limit exceeded: bucket=%s limit=%d path=%s %s",
                    auth_key,
                    auth_max,
                    request.method,
                    path,
                )
                return self._build_429_response(auth_result)

        # Principal resolution (only after the auth-floor check, to avoid decoding tokens on
        # requests we've already decided to reject).
        principal_resolver: PrincipalResolver = request.app.state.principal_resolver
        access_token = request.cookies.get("access_token")
        principal = await principal_resolver.resolve(access_token, client_ip)

        # Principal bucket (exactly one of the two).
        if principal.kind == "user":
            principal_key = f"user:{principal.id}:api"
            principal_limit = user_max
        else:
            principal_key = f"ip:{principal.id}:api"
            principal_limit = unauth_max
        principal_result = rate_limiter.check(principal_key, principal_limit, window)
        if principal_result.is_limited:
            logger.warning(
                "Rate limit exceeded: bucket=%s limit=%d path=%s %s",
                principal_key,
                principal_limit,
                request.method,
                path,
            )
            return self._build_429_response(principal_result)

        response = await call_next(request)

        # Surface the principal bucket's state in headers (the user-facing one).
        response.headers["X-RateLimit-Limit"] = str(principal_result.limit)
        response.headers["X-RateLimit-Remaining"] = str(principal_result.remaining)
        return response

    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.EXEMPT_PREFIXES)

    @staticmethod
    def _build_429_response(result: RateLimitResult) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."},
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(result.retry_after),
            },
        )
