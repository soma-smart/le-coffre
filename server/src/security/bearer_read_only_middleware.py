"""Refuse mutating requests that authenticate with a bearer token.

This looks redundant next to `ApiPrincipal.ensure_method_allowed`, and it is
not. Please read before deleting it.

`CsrfMiddleware` only engages when a session cookie is present (see its
`dispatch`: no access_token and no refresh_token means it steps aside and lets
the route return 401). A bearer request carries no cookies, so the entire bearer
class falls outside CSRF *by construction*.

That is fine only while a bearer can never reach a mutating route. Today that
invariant is enforced by a FastAPI dependency, one layer below where the
invariant it replaces used to live. This middleware restores it at the original
layer, so the guarantee does not depend on every future route author picking the
right dependency.

No exemptions are needed: the pairing endpoints are POSTs but carry no bearer.
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class BearerReadOnlyMiddleware(BaseHTTPMiddleware):
    """Bearer credentials are read-only, enforced before routing."""

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
    PROTECTED_PREFIX = "/api"

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() in self.SAFE_METHODS:
            return await call_next(request)

        if not request.url.path.startswith(self.PROTECTED_PREFIX):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        # Scheme comparison is case-insensitive per RFC 7235; `Bearer`, `bearer`
        # and `BEARER` are the same credential.
        if not authorization.lower().startswith("bearer "):
            return await call_next(request)

        logger.warning(
            "Rejected a mutating request authenticated with a bearer token: %s %s",
            request.method,
            _sanitize_path(request.url.path),
        )
        return JSONResponse(
            status_code=403,
            content={"detail": "This credential is read-only and cannot perform a mutating request"},
        )


def _sanitize_path(path: str) -> str:
    """Truncate to at most 3 segments so resource IDs never reach the log."""
    parts = path.split("/")
    return "/".join(parts[:4])
