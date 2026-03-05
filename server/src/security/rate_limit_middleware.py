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

    Every ``/api`` request is checked against a general **API bucket** keyed by
    the caller's IP (``ip:<ip>:api``).  Authentication routes additionally go
    through a stricter **auth bucket** (``ip:<ip>:auth``) to mitigate
    brute-force and credential-stuffing attacks.  For non-auth routes, when the
    caller carries a valid ``access_token`` cookie, an additional **per-user
    bucket** (``user:<id>:api``) is also enforced so that a single compromised
    account cannot exhaust the shared IP quota.

    After a **successful login** (2xx on ``/api/auth/login``) only the auth
    bucket is reset so shared IPs (e.g. office NAT) are not locked out of the
    login page.  The API and user buckets are intentionally kept intact.

    Health-check and documentation endpoints are exempt from all limiting.
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
        api_max = request.app.state.rate_limit_api_max_requests
        auth_max = request.app.state.rate_limit_auth_max_requests
        window = request.app.state.rate_limit_window_seconds

        client_ip = self._get_client_ip(request)
        is_auth_route = self._is_auth_route(request.url.path)
        api_key = f"ip:{client_ip}:api"
        auth_key = f"ip:{client_ip}:auth"

        # ── General API check (all /api routes) ────────────────
        api_result = rate_limiter.check(api_key, api_max, window)
        if api_result.is_limited:
            logger.warning(
                "Rate limit exceeded for IP %s on %s %s",
                client_ip,
                request.method,
                request.url.path,
            )
            return self._build_429_response(api_result)

        # ── Additional auth check (auth routes only) ────────────
        auth_result = None
        if is_auth_route:
            auth_result = rate_limiter.check(auth_key, auth_max, window)
            if auth_result.is_limited:
                logger.warning(
                    "Rate limit exceeded for IP %s on %s %s",
                    client_ip,
                    request.method,
                    request.url.path,
                )
                return self._build_429_response(auth_result)

        # ── Per-user check (non-auth routes only) ───────────────
        if not is_auth_route:
            user_id = await self._try_extract_user_id(request)
            if user_id:
                user_key = f"user:{user_id}:api"
                user_result = rate_limiter.check(user_key, api_max, window)
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

        # Expose the most relevant limit: auth bucket for auth routes, API bucket otherwise
        header_result = auth_result if auth_result is not None else api_result
        response.headers["X-RateLimit-Limit"] = str(header_result.limit)
        response.headers["X-RateLimit-Remaining"] = str(header_result.remaining)

        # On successful login reset only the auth bucket; the API bucket keeps counting
        if request.url.path == "/api/auth/login" and response.status_code < 300:
            rate_limiter.reset_key(auth_key)

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
        Returns ``None`` if the token is absent, expired, invalid, or if no
        ``token_gateway`` is configured — rate limiting then relies solely on
        the IP-based check.
        """
        access_token = request.cookies.get("access_token")
        if not access_token:
            return None

        try:
            token_gateway = request.app.state.token_gateway
            if token_gateway is None:
                return None
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
