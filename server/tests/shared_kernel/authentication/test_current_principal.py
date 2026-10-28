"""The opt-in token path, and its containment rules.

Only the routes depending on `get_current_principal`, or on a dependency built
on the same authentication, accept a bearer token. These tests pin the rules
that make that safe, including which routes those are.
"""

from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from identity_access_management_context.application.responses import (
    AuthenticateTokenResponse,
    ValidateUserTokenResponse,
)
from identity_access_management_context.application.use_cases import (
    AuthenticateTokenUseCase,
    ValidateUserTokenUseCase,
)
from main import app
from security.rate_limit_middleware import RateLimitMiddleware
from shared_kernel.adapters.primary.dependencies import (
    _authenticate,
    get_current_credential,
    get_current_principal,
    get_current_requesting_user,
    get_current_service_account,
)
from shared_kernel.domain.entities import AuthenticatedPrincipal, AuthenticatedUser, PresentedCredential
from shared_kernel.domain.exceptions import RejectedCredentialError

USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
CREDENTIAL_ID = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")


def _request(method: str = "GET", authorization: str | None = None):
    request = Mock()
    request.method = method
    request.headers = {} if authorization is None else {"Authorization": authorization}
    return request


def _session_usecase(roles: list[str]):
    usecase = Mock(spec=ValidateUserTokenUseCase)
    usecase.execute = Mock(
        return_value=ValidateUserTokenResponse(
            is_valid=True,
            user_id=USER_ID,
            email="admin@lecoffre.com",
            display_name="Admin User",
            roles=roles,
        )
    )
    return usecase


def _token_usecase(read_only: bool = True, roles: list[str] | None = None, kind: str = "user"):
    usecase = Mock(spec=AuthenticateTokenUseCase)
    usecase.execute = Mock(
        return_value=AuthenticateTokenResponse(
            principal_id=USER_ID,
            principal_kind=kind,
            roles=["admin"] if roles is None else roles,
            credential_id=CREDENTIAL_ID,
            read_only=read_only,
        )
    )
    return usecase


def _bearer(value: str = "a-token"):
    return f"Bearer {value}"


def _authenticate_with(method="GET", access_token=None, credentials=None, session=None, token=None):
    return _authenticate(
        request=_request(method, credentials),
        access_token=access_token,
        client_ip="203.0.113.7",
        validate_usecase=session or _session_usecase(["admin"]),
        authenticate_token_usecase=token or _token_usecase(),
    )


def test_should_resolve_the_user_with_its_roles_when_the_cookie_is_valid():
    authentication = _authenticate_with(access_token="valid-cookie")

    assert get_current_principal(authentication) == AuthenticatedPrincipal(principal_id=USER_ID, kind="user")
    assert get_current_credential(authentication) is None
    assert get_current_requesting_user(authentication) == AuthenticatedUser(user_id=USER_ID, roles=["admin"])


def test_should_not_fall_back_to_the_token_when_the_cookie_is_invalid():
    """A cookie wins, and a bad one is fatal: a token must not rescue it."""
    session = Mock(spec=ValidateUserTokenUseCase)
    session.execute = Mock(side_effect=Exception("expired"))
    token = _token_usecase()

    with pytest.raises(HTTPException):
        _authenticate_with(access_token="expired-cookie", credentials=_bearer(), session=session, token=token)

    token.execute.assert_not_called()


def test_should_refuse_when_neither_cookie_nor_token_is_presented():
    with pytest.raises(HTTPException) as error:
        _authenticate_with()

    assert error.value.status_code == 401


def test_should_resolve_the_principal_and_its_credential_when_the_token_is_valid():
    authentication = _authenticate_with(credentials=_bearer())

    assert get_current_principal(authentication) == AuthenticatedPrincipal(principal_id=USER_ID, kind="user")
    assert get_current_credential(authentication) == PresentedCredential(credential_id=CREDENTIAL_ID, read_only=True)


def test_should_drop_the_roles_when_the_token_is_read_only():
    """An admin's extension must not make `/passwords/list` return every secret of the instance."""
    authentication = _authenticate_with(credentials=_bearer(), token=_token_usecase(read_only=True, roles=["admin"]))

    assert get_current_requesting_user(authentication).roles == []


def test_should_keep_the_roles_when_the_token_is_not_read_only():
    authentication = _authenticate_with(credentials=_bearer(), token=_token_usecase(read_only=False, roles=["admin"]))

    assert get_current_requesting_user(authentication).roles == ["admin"]


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_should_refuse_a_mutating_request_when_the_token_is_read_only(method):
    with pytest.raises(HTTPException) as error:
        _authenticate_with(method=method, credentials=_bearer(), token=_token_usecase(read_only=True))

    assert error.value.status_code == 403


def test_should_answer_one_generic_401_when_the_token_is_refused():
    token = Mock(spec=AuthenticateTokenUseCase)
    token.execute = Mock(side_effect=RejectedCredentialError())

    with pytest.raises(HTTPException) as error:
        _authenticate_with(credentials=_bearer(), token=token)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid token"


def test_should_refuse_a_route_meant_for_users_when_the_principal_is_a_service_account():
    authentication = _authenticate_with(credentials=_bearer(), token=_token_usecase(kind="service_account"))

    with pytest.raises(HTTPException) as error:
        get_current_requesting_user(authentication)

    assert error.value.status_code == 403


def test_should_match_the_rate_limiter_when_listing_the_bearer_reachable_routes():
    """The list of bearer-reachable paths lives in two places. Keep them equal.

    `RateLimitMiddleware` has to know which routes can authenticate a bearer, so
    it does not spend a database lookup deciding the bucket of a request that is
    going to 401 anyway. That knowledge really lives in the route declarations,
    and a copy of it in the middleware is exactly the kind of restatement that
    drifts in silence.

    Deriving the truth from the application's own dependency graph also pins the
    containment rule itself: if somebody makes a route depend on the token
    authentication, this test says so.
    """

    def api_routes(routes):
        # FastAPI 0.141 keeps an included router wrapped rather than flattening
        # its routes into app.routes, so the real ones hang off original_router.
        # If a future version changes that shape, this yields nothing and the
        # assertion below fails loudly; it cannot quietly pass.
        for route in routes:
            if isinstance(route, APIRoute):
                yield route
            included = getattr(route, "original_router", None)
            if included is not None:
                yield from api_routes(included.routes)

    def accepts_a_token(dependant) -> bool:
        if dependant.call in (_authenticate, get_current_service_account):
            return True
        return any(accepts_a_token(child) for child in dependant.dependencies)

    reachable = {route.path for route in api_routes(app.routes) if accepts_a_token(route.dependant)}

    assert reachable == {
        "/extension/session",
        "/extension/groups",
        "/passwords/list",
        "/passwords/{password_id}",
        "/iam/service-accounts/me",
    }

    # Every one of them must be covered by the middleware's filter. Paths here
    # carry no /api prefix; the middleware sees the externally-visible path,
    # because the application runs with root_path="/api" and uvicorn leaves it
    # in the scope.
    for path in reachable:
        assert RateLimitMiddleware._is_bearer_reachable("GET", f"/api{path}"), (
            f"{path} accepts a bearer but the rate limiter refuses to resolve one there, "
            "so its callers silently fall into the anonymous bucket"
        )
