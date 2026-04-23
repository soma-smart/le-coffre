"""Rate-limiting middleware for FastAPI.

Three mutually-exclusive principal buckets plus an auth-route floor govern
every non-exempt ``/api/*`` request:

- ``user:<id>:api``   — requests with a valid ``access_token`` cookie (per-user bucket).
- ``ip:<client_ip>:api`` — requests without a valid token (per-IP bucket).
- ``ip:<client_ip>:auth`` — runs *in addition* on ``/api/auth/login`` only (the
  auth-route volume floor).

The client IP is extracted via :func:`resolve_client_ip`, which honors
``X-Forwarded-For`` only when the direct TCP peer is in
``app.state.rate_limit_trusted_proxies``.  The current datetime comes from
``app.state.time_provider`` so the middleware never reads a real clock — tests
use :class:`UtcTimeGateway` directly, no monkeypatching needed.

Principal resolution is inline: if the access-token cookie decodes against
``app.state.token_gateway``, the request is keyed on ``user:<id>:api``;
otherwise on ``ip:<client_ip>:api``.  Keeping this inline avoids a dedicated
cross-context private-API seam — the middleware is a primary adapter that's
allowed to read primary-adapter state directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from identity_access_management_context.domain.exceptions import InvalidTokenException
from security.client_ip import resolve_client_ip
from security.rate_limiter import InMemoryRateLimiter, RateLimitResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Principal:
    kind: Literal["user", "ip"]
    id: str


class RateLimitMiddleware(BaseHTTPMiddleware):
    """See module docstring."""

    # Only password login consumes the auth-route floor.  Every other /auth/*
    # endpoint (register-admin, refresh-token, sso/callback, sso/url,
    # sso/is-configured, sso/configure) falls through to the principal bucket —
    # brute-force defense against a specific account lives in the IAM
    # LoginLockoutGateway, not here.
    AUTH_ROUTES: tuple[str, ...] = ("/api/auth/login",)

    # Frequently-polled read-only endpoints that every page / pre-login flow hits:
    # exempting them prevents the normal UI from burning through its IP bucket
    # on routine state checks.  Mutating or credential-submitting endpoints
    # obviously stay rate-limited.
    # Paths are matched against ``request.url.path`` as it enters the middleware,
    # which is the externally-visible path (the backend runs with
    # ``root_path="/api"`` but uvicorn does not strip it from the scope), so
    # every prefix here includes the ``/api`` prefix — including the FastAPI
    # docs/openapi routes, which are served at ``/api/docs`` and
    # ``/api/openapi.json`` in this deployment.
    EXEMPT_PREFIXES: tuple[str, ...] = (
        "/api/health",
        "/api/vault/status",
        "/api/auth/sso/url",
        "/api/auth/sso/is-configured",
        "/api/docs",
        "/api/openapi",
    )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if self._is_exempt(path):
            return await call_next(request)

        if not path.startswith("/api"):
            return await call_next(request)

        # app.state attrs are wired in lifespan; if that regresses we want a
        # CRITICAL with exc_info rather than an anonymous 500.
        try:
            rate_limiter: InMemoryRateLimiter = request.app.state.rate_limiter
            user_max = request.app.state.rate_limit_user_max_requests
            unauth_max = request.app.state.rate_limit_unauth_max_requests
            auth_max = request.app.state.rate_limit_auth_max_requests
            window = request.app.state.rate_limit_window_seconds
            trusted_proxies = request.app.state.rate_limit_trusted_proxies
            proxy_hops = request.app.state.rate_limit_trusted_proxy_hops
            time_provider = request.app.state.time_provider
        except AttributeError:
            logger.critical(
                "RateLimitMiddleware misconfigured: app.state missing required rate_limit_* keys; "
                "failing request closed with 500 — check lifespan wiring",
                exc_info=True,
            )
            raise

        now = time_provider.get_current_time()
        client_ip = resolve_client_ip(request, trusted_proxies=trusted_proxies, hops=proxy_hops)
        is_auth_route = path in self.AUTH_ROUTES

        # Auth-route floor runs first so a flood on /api/auth/login doesn't pay
        # the JWT-decode cost on every rejected request.
        if is_auth_route:
            auth_key = f"ip:{client_ip}:auth"
            auth_result = rate_limiter.check(auth_key, auth_max, window, now=now)
            if auth_result.is_limited:
                logger.warning(
                    "Rate limit exceeded: bucket=%s limit=%d path=%s %s",
                    auth_key,
                    auth_max,
                    request.method,
                    path,
                )
                return self._build_429_response(auth_result)

        principal = await self._resolve_principal(request, client_ip)
        if principal.kind == "user":
            principal_key = f"user:{principal.id}:api"
            principal_limit = user_max
        else:
            principal_key = f"ip:{principal.id}:api"
            principal_limit = unauth_max
        principal_result = rate_limiter.check(principal_key, principal_limit, window, now=now)
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
        response.headers["X-RateLimit-Limit"] = str(principal_result.limit)
        response.headers["X-RateLimit-Remaining"] = str(principal_result.remaining)
        return response

    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.EXEMPT_PREFIXES)

    @staticmethod
    async def _resolve_principal(request: Request, client_ip: str) -> Principal:
        access_token = request.cookies.get("access_token")
        if not access_token:
            return Principal(kind="ip", id=client_ip)
        token_gateway = getattr(request.app.state, "token_gateway", None)
        if token_gateway is None:
            return Principal(kind="ip", id=client_ip)
        try:
            token = await token_gateway.validate_token(access_token)
        except InvalidTokenException:
            # Expected path: domain-level "expired/tampered/unknown-issuer" signal.
            # Bucket as anonymous silently — every user with an expired cookie
            # traverses this code and we don't want to alert on normal traffic.
            token = None
        except Exception:  # noqa: BLE001 - fail-closed to IP keying; surface at WARNING
            # Unexpected (JWT lib bug, secret rotation, future remote gateway).
            # Silent swallowing hides key-rotation incidents that only manifest
            # as "every authenticated user mysteriously rate-limited".
            logger.warning(
                "Token gateway raised non-validation error during rate-limit keying; bucketing as anonymous",
                exc_info=True,
            )
            token = None
        if token:
            return Principal(kind="user", id=str(token.user_id))
        return Principal(kind="ip", id=client_ip)

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
