from typing import Literal, TypeVar

from starlette.requests import Request
from starlette.responses import Response

SameSite = Literal["lax", "strict", "none"]
ResponseT = TypeVar("ResponseT", bound=Response)

_REVOCATIONS_SCOPE_KEY = "cookie_revocations"


def revoke_cookie(request: Request, response: Response, key: str, *, secure: bool, samesite: SameSite) -> None:
    """
    Clear a cookie whether the endpoint returns or raises.

    ``response.delete_cookie`` alone only reaches the client on the success path:
    raising ``HTTPException`` makes the global handler build a fresh JSONResponse,
    which drops everything staged on the injected Response. Recording the
    revocation on the request lets that handler replay it.

    This matters most for httpOnly cookies — the server is the only actor able to
    clear them, since no frontend code can touch them.
    """
    response.delete_cookie(key, secure=secure, samesite=samesite)
    revocations = getattr(request.state, _REVOCATIONS_SCOPE_KEY, None)
    if revocations is None:
        revocations = []
        setattr(request.state, _REVOCATIONS_SCOPE_KEY, revocations)
    revocations.append((key, secure, samesite))


def replay_cookie_revocations(request: Request, response: ResponseT) -> ResponseT:
    """Re-apply on ``response`` the revocations staged during the request."""
    for key, secure, samesite in getattr(request.state, _REVOCATIONS_SCOPE_KEY, ()):
        response.delete_cookie(key, secure=secure, samesite=samesite)
    return response
