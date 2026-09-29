"""Rate-limiting middleware for FastAPI.

Three mutually-exclusive principal buckets plus an auth-route floor govern
every non-exempt ``/api/*`` request:

- ``user:<id>:api``   , requests with a valid ``access_token`` cookie, or a valid
  browser-extension bearer token (per-user bucket).
- ``ip:<client_ip>:api`` — requests without a valid token (per-IP bucket).
- ``ip:<client_ip>:auth`` — runs *in addition* on ``/api/auth/login`` only (the
  auth-route volume floor).

The client IP is extracted via :func:`resolve_client_ip`, which honors
``X-Forwarded-For`` only when the direct TCP peer is in
``app.state.rate_limit_trusted_proxies``.  The current datetime comes from
``app.state.time_provider`` so the middleware never reads a real clock — tests
use :class:`UtcTimeGateway` directly, no monkeypatching needed.

Principal resolution is inline: if the access-token cookie decodes against
``app.state.token_gateway``, the request is keyed on ``user:<id>:api``.  Failing
that, a browser-extension bearer token is resolved against the database, since
an extension cannot send cookies at all (they are ``SameSite=strict``) and would
otherwise be stuck in the anonymous bucket, which is unusable behind a NAT.
Everything else keys on ``ip:<client_ip>:api``.  Keeping this inline avoids a
dedicated cross-context private-API seam: the middleware is a primary adapter
that's allowed to read primary-adapter state directly.

That lookup is the only database access in this middleware, and it happens
before any bucket has been consulted, on a request that may carry no valid
credential at all.  Three guards bound it, all in
``_resolve_bearer_principal``: it runs only on the handful of routes where a
bearer can authenticate (``BEARER_REACHABLE_PATHS``); a token seen working in
the last minute answers from :class:`BearerPrincipalCache` without any query;
and a per-IP budget charged *only for lookups that find nothing* stops a caller
guessing tokens from buying unlimited queries.  The cache is checked before the
budget on purpose, so that spending the budget from a shared address cannot
demote a colleague's working extension into the bucket the attacker just
filled.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from identity_access_management_context.adapters.secondary.sql import SqlExtensionTokenRepository
from identity_access_management_context.domain.exceptions import (
    InvalidExtensionTokenError,
    InvalidTokenException,
)
from identity_access_management_context.domain.value_objects import ExtensionTokenSecret
from security.bearer_principal_cache import BearerPrincipalCache
from security.client_ip import resolve_client_ip
from security.rate_limiter import InMemoryRateLimiter, RateLimitResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Principal:
    kind: Literal["user", "ip"]
    id: str


class RateLimitMiddleware(BaseHTTPMiddleware):
    """See module docstring."""

    def __init__(self, app, bearer_cache: BearerPrincipalCache | None = None) -> None:
        super().__init__(app)
        # Owned by the middleware rather than app.state: nothing else reads it,
        # it needs no configuration, and one instance per application is exactly
        # what BaseHTTPMiddleware construction already gives us.
        self._bearer_cache = bearer_cache or BearerPrincipalCache()

    # Only password login consumes the auth-route floor.  Every other /auth/*
    # endpoint (register-admin, refresh-token, sso/callback, sso/url,
    # sso/is-configured, sso/configure) falls through to the principal bucket —
    # brute-force defense against a specific account lives in the IAM
    # LoginLockoutGateway, not here.
    AUTH_ROUTES: tuple[str, ...] = ("/api/auth/login",)

    # Vault-mutation endpoints share a strict per-IP floor. These are the
    # (mostly unauthenticated) unlock/setup surfaces abused for DoS: looped
    # `/vault/unlock/clear`, share-pool pollution via `/vault/unlock`, and
    # `/vault/setup` re-init flooding. `/api/vault/unlock` covers both
    # `/unlock` and `/unlock/clear`. `/api/vault/status` stays exempt (polled).
    VAULT_MUTATION_PREFIXES: tuple[str, ...] = (
        "/api/vault/unlock",
        "/api/vault/setup",
        "/api/vault/validate-setup",
    )

    # Destructive vault operations throttled by a single GLOBAL bucket (all callers
    # and all IPs share it), enforcing "at most once per window" across both ops.
    # This is what stops the DoS: an attacker cannot loop the anonymous
    # `/vault/unlock/clear` to wipe accumulated shares, nor loop `/vault/setup` to
    # overwrite a setup in progress — regardless of how many IPs they rotate through.
    VAULT_SENSITIVE_OPS: dict[tuple[str, str], str] = {
        ("DELETE", "/api/vault/unlock/clear"): "vault:sensitive",
        ("POST", "/api/vault/setup"): "vault:sensitive",
    }

    # Redeeming a one-time link is anonymous, so it would otherwise share the
    # generic unauthenticated per-IP bucket with the recipient's normal browsing.
    # Its own per-IP floor keeps several recipients behind one NAT working while
    # bounding abuse of the endpoint.
    ONE_TIME_LINK_CONSUME_OPS: tuple[tuple[str, str], ...] = (("POST", "/api/one-time-links/consume"),)

    # Anonymous browser-extension pairing. Same reasoning as the one-time link
    # floor: no session exists yet, so without a bucket of its own the polling
    # loop competes with every other unauthenticated caller behind the same NAT.
    EXTENSION_PAIRING_OPS: tuple[tuple[str, str], ...] = (
        ("POST", "/api/extension/device"),
        ("POST", "/api/extension/device/exchange"),
    )

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

    # The routes that declare `Depends(get_current_principal)`, i.e. the only
    # ones where a bearer can authenticate anything. Resolving a bearer anywhere
    # else is a database round trip for a request that is going to 401 no matter
    # what the lookup says, and it is reachable without credentials, so it is
    # free work an anonymous caller can ask for.
    #
    # `/api/passwords/` is a prefix because `GET /passwords/{password_id}` is
    # parameterised. It therefore also covers a couple of sibling GETs that a
    # bearer cannot actually reach; erring wide here is cheap, and the miss
    # budget in _resolve_bearer_principal bounds the difference.
    #
    # Kept honest by test_bearer_reachable_paths_match_the_routes, which derives
    # the real set from the application's dependency graph. Without it this is a
    # second place stating a rule that lives in the route declarations.
    BEARER_REACHABLE_PATHS: tuple[str, ...] = (
        "/api/extension/session",
        "/api/extension/groups",
    )
    BEARER_REACHABLE_PREFIXES: tuple[str, ...] = ("/api/passwords/",)

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
            vault_max = request.app.state.rate_limit_vault_max_requests
            sensitive_max = request.app.state.rate_limit_vault_sensitive_max_requests
            sensitive_window = request.app.state.rate_limit_vault_sensitive_window_seconds
            one_time_link_max = request.app.state.rate_limit_one_time_link_max_requests
            extension_pairing_max = request.app.state.rate_limit_extension_pairing_max_requests
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
                    "Rate limit exceeded: bucket=%s limit=%d method=%s path=%s",
                    auth_key,
                    auth_max,
                    request.method,
                    path,
                )
                return self._build_429_response(auth_result)

        # Global throttle on destructive vault operations (clear / setup): a single
        # shared bucket enforcing at-most-once-per-window across all callers. Checked
        # before the per-IP floor so a throttled request consumes nothing else.
        sensitive_key = self.VAULT_SENSITIVE_OPS.get((request.method, path))
        if sensitive_key is not None:
            sensitive_result = rate_limiter.check(sensitive_key, sensitive_max, sensitive_window, now=now)
            if sensitive_result.is_limited:
                logger.warning(
                    "Rate limit exceeded: bucket=%s limit=%d method=%s path=%s",
                    sensitive_key,
                    sensitive_max,
                    request.method,
                    path,
                )
                return self._build_429_response(sensitive_result)

        # Vault-mutation floor: a strict per-IP bucket in addition to the
        # principal bucket, defeating the unauthenticated unlock/setup DoS
        # vectors before they reach the (in-memory) share state.
        if self._is_vault_mutation(path):
            vault_key = f"ip:{client_ip}:vault"
            vault_result = rate_limiter.check(vault_key, vault_max, window, now=now)
            if vault_result.is_limited:
                logger.warning(
                    "Rate limit exceeded: bucket=%s limit=%d method=%s path=%s",
                    vault_key,
                    vault_max,
                    request.method,
                    path,
                )
                return self._build_429_response(vault_result)

        # One-time link redemption floor: per-IP, checked before the principal
        # bucket so a flood here does not also exhaust the caller's generic quota.
        # Extension pairing floor: per-IP, same rationale as the one-time link
        # floor below. Both pairing endpoints are anonymous by design.
        if (request.method, path) in self.EXTENSION_PAIRING_OPS:
            extension_pairing_key = f"ip:{client_ip}:extension-pairing"
            extension_pairing_result = rate_limiter.check(extension_pairing_key, extension_pairing_max, window, now=now)
            if extension_pairing_result.is_limited:
                logger.warning(
                    "Rate limit exceeded: bucket=%s limit=%d method=%s path=%s",
                    extension_pairing_key,
                    extension_pairing_max,
                    request.method,
                    path,
                )
                return self._build_429_response(extension_pairing_result)

        if (request.method, path) in self.ONE_TIME_LINK_CONSUME_OPS:
            one_time_link_key = f"ip:{client_ip}:one-time-link"
            one_time_link_result = rate_limiter.check(one_time_link_key, one_time_link_max, window, now=now)
            if one_time_link_result.is_limited:
                logger.warning(
                    "Rate limit exceeded: bucket=%s limit=%d method=%s path=%s",
                    one_time_link_key,
                    one_time_link_max,
                    request.method,
                    path,
                )
                return self._build_429_response(one_time_link_result)

        principal = self._resolve_principal(request, client_ip)
        if principal.kind == "user":
            principal_key = f"user:{principal.id}:api"
            principal_limit = user_max
        else:
            principal_key = f"ip:{principal.id}:api"
            principal_limit = unauth_max
        principal_result = rate_limiter.check(principal_key, principal_limit, window, now=now)
        if principal_result.is_limited:
            logger.warning(
                "Rate limit exceeded: bucket=%s limit=%d method=%s path=%s",
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

    @classmethod
    def _is_bearer_reachable(cls, method: str, path: str) -> bool:
        """Could a bearer authenticate this request at all?

        The method half is not redundant with BearerReadOnlyMiddleware, which
        403s a mutating bearer request: main.py adds this middleware last, so it
        runs FIRST, and a POST carrying a bearer would otherwise pay for the
        lookup before the other middleware ever sees it.
        """
        if method.upper() != "GET":
            return False
        return path in cls.BEARER_REACHABLE_PATHS or any(
            path.startswith(prefix) for prefix in cls.BEARER_REACHABLE_PREFIXES
        )

    def _is_vault_mutation(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.VAULT_MUTATION_PREFIXES)

    def _resolve_principal(self, request: Request, client_ip: str) -> Principal:
        access_token = request.cookies.get("access_token")
        token_gateway = getattr(request.app.state, "token_gateway", None)

        if access_token and token_gateway is not None:
            try:
                token = token_gateway.validate_token(access_token)
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

        # No cookie at all is the EXTENSION's normal case, not an edge one: its
        # requests carry a bearer and never a cookie, because cookies here are
        # SameSite=strict. An earlier version returned the IP principal right
        # here whenever the cookie was absent, which made the whole function
        # below unreachable for the only caller it was written for, and left
        # every extension in the shared anonymous bucket. Do not reinstate that
        # early return: it looks free and costs the feature.
        return self._resolve_bearer_principal(request, client_ip)

    def _resolve_bearer_principal(self, request: Request, client_ip: str) -> Principal:
        """Key a browser-extension caller to its user, not to its IP.

        Without this the extension lands in the 30/min anonymous IP bucket
        instead of the 300/min per-user one, which is unusable behind a
        corporate NAT where every colleague shares one address.

        Fails closed to IP keying in every doubtful case: this decides which
        bucket to charge, never whether the request is allowed.

        Everything below the two guards is a database round trip on an
        unauthenticated request, so both guards run before any header is even
        parsed. See BEARER_REACHABLE_PATHS and the miss budget.
        """
        if not self._is_bearer_reachable(request.method, request.url.path):
            return Principal(kind="ip", id=client_ip)

        authorization = request.headers.get("Authorization", "")
        if not authorization.lower().startswith("bearer "):
            return Principal(kind="ip", id=client_ip)

        # The value object owns both the shape of a token and how it hashes.
        # Restating either here is how the two drift: an earlier version of this
        # file gated on `len == 43` while the value object gates on `>= 43`, and
        # a change to TOKEN_BYTES or to the digest would have left auth working
        # while every extension silently dropped from the per-user bucket into
        # the anonymous IP one, with nothing logged.
        try:
            secret = ExtensionTokenSecret(value=authorization[7:].strip())
        except InvalidExtensionTokenError:
            # Cheap format gate before any database access, so junk bearers
            # never reach a query. An attacker sending well-formed unknown
            # tokens still falls back to the IP bucket, which caps them at the
            # anonymous limit.
            return Principal(kind="ip", id=client_ip)

        # A miss budget, not a request budget. Consumed only when the lookup
        # comes back empty, so a caller guessing tokens spends it in a few
        # requests and then stops reaching the database. Exhausting it degrades
        # to IP keying rather than to a 429: this function decides which bucket
        # to charge, never whether the request is allowed.
        miss_key = f"ip:{client_ip}:bearer-miss"
        token_hash = secret.hashed()
        try:
            rate_limiter = request.app.state.rate_limiter
            miss_max = request.app.state.rate_limit_bearer_miss_max_requests
            window = request.app.state.rate_limit_window_seconds
            time_provider = request.app.state.time_provider
            now = time_provider.get_current_time()

            # Before the budget, deliberately. A token seen working recently
            # must not be held hostage by somebody else on the same address
            # spending that budget: without this, exhausting the budget from a
            # shared NAT would push every colleague's extension into the
            # anonymous bucket the attacker has just filled, turning the guard
            # into a sharper attack than the one it prevents.
            cached_user_id = self._bearer_cache.get(token_hash, now)
            if cached_user_id is not None:
                return Principal(kind="user", id=cached_user_id)

            if rate_limiter.is_exhausted(miss_key, miss_max, window, now):
                return Principal(kind="ip", id=client_ip)

            session_maker = request.app.state.session_maker
            with session_maker() as session:
                token_row = SqlExtensionTokenRepository(session).get_by_token_hash(token_hash)
        except Exception:  # noqa: BLE001 - bucket selection must never fail a request
            logger.warning(
                "Could not resolve an extension token for rate-limit keying; bucketing as anonymous",
                exc_info=True,
            )
            return Principal(kind="ip", id=client_ip)

        if token_row is None or not token_row.is_active(now):
            # The lookup was wasted. Charge it, so a caller producing nothing
            # but misses runs out of budget while a real extension never does.
            rate_limiter.check(miss_key, miss_max, window, now)
            return Principal(kind="ip", id=client_ip)

        user_id = str(token_row.user_id)
        self._bearer_cache.put(token_hash, user_id, now)
        return Principal(kind="user", id=user_id)

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
