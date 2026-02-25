"""Rate limiting middleware for FastAPI."""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from security.rate_limiter import InMemoryRateLimiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using a sliding window counter.

    Applies two independent checks per request:
    1. **IP-based** – every request is rate-limited by the caller's IP
       address so that anonymous and authenticated traffic is both bounded.
    2. **User-based** – when the caller carries a valid ``access_token``
       cookie, an additional per-user limit is enforced.  The user ID is
       extracted from the JWT *without* a database round-trip.

    Authentication routes (login, register, SSO) are subject to a stricter
    limit to mitigate brute-force attacks.  Health-check and documentation
    endpoints are exempt.
    """

    AUTH_ROUTES = [
        "/api/auth/login",
        "/api/auth/register-admin",
        "/api/auth/refresh-token",
        "/api/auth/sso",
    ]

    EXEMPT_ROUTES = [
        "/api/health",
        "/docs",
        "/openapi",
    ]

    async def dispatch(self, request: Request, call_next):
        """Process the request and apply rate limiting."""

        # Skip exempt routes
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Only rate-limit /api routes
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        rate_limiter: InMemoryRateLimiter = request.app.state.rate_limiter
        auth_max = request.app.state.rate_limit_auth_max_requests
        api_max = request.app.state.rate_limit_api_max_requests
        window = request.app.state.rate_limit_window_seconds

        is_auth_route = self._is_auth_route(request.url.path)
        max_requests = auth_max if is_auth_route else api_max

        # ── IP-based check ──────────────────────────────────────
        client_ip = self._get_client_ip(request)
        category = "auth" if is_auth_route else "api"
        ip_key = f"ip:{client_ip}:{category}"
        ip_result = rate_limiter.check(ip_key, max_requests, window)

        if ip_result.is_limited:
            logger.warning(
                "Rate limit exceeded for IP %s on %s %s",
                client_ip,
                request.method,
                request.url.path,
            )
            return self._build_429_response(ip_result)

        # ── User-based check ───────────────────────────────────
        user_id = await self._try_extract_user_id(request)
        if user_id:
            user_key = f"user:{user_id}:{category}"
            user_result = rate_limiter.check(user_key, max_requests, window)

            if user_result.is_limited:
                logger.warning(
                    "Rate limit exceeded for user %s on %s %s",
                    user_id,
                    request.method,
                    request.url.path,
                )
                return self._build_429_response(user_result)

        # ── Proceed ────────────────────────────────────────────
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(ip_result.limit)
        response.headers["X-RateLimit-Remaining"] = str(ip_result.remaining)
        return response

    # ── Helpers ─────────────────────────────────────────────────

    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(route) for route in self.EXEMPT_ROUTES)

    def _is_auth_route(self, path: str) -> bool:
        return any(path.startswith(route) for route in self.AUTH_ROUTES)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    @staticmethod
    async def _try_extract_user_id(request: Request) -> str | None:
        """
        Best-effort extraction of the user ID from the JWT cookie.

        Uses the ``token_gateway`` stored in app state to decode the token.
        Returns ``None`` if the token is absent, expired or invalid — rate
        limiting then relies solely on the IP-based check.
        """
        access_token = request.cookies.get("access_token")
        if not access_token:
            return None

        try:
            token_gateway = request.app.state.token_gateway
            token = await token_gateway.validate_token(access_token)
            if token:
                return str(token.user_id)
        except Exception:
            pass
        return None

    @staticmethod
    def _build_429_response(result) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."},
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(result.retry_after),
            },
        )
