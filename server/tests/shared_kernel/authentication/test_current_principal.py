"""The opt-in bearer path, and its containment rules.

`get_current_principal` is the only dependency that accepts a browser-extension
bearer token, and only four read routes declare it. These tests pin the rules
that make that safe, including which routes those four are.
"""

from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from identity_access_management_context.application.responses import (
    ValidatedExtensionTokenResponse,
    ValidateUserTokenResponse,
)
from identity_access_management_context.application.use_cases import (
    ValidateExtensionTokenUseCase,
    ValidateUserTokenUseCase,
)
from identity_access_management_context.domain.exceptions import ExtensionTokenRevokedError
from shared_kernel.adapters.primary.dependencies import get_current_principal
from shared_kernel.domain.value_objects import CredentialKind

USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
TOKEN_ID = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")


def _request(method: str = "GET"):
    request = Mock()
    request.method = method
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


def _extension_usecase():
    usecase = Mock(spec=ValidateExtensionTokenUseCase)
    usecase.execute = Mock(
        return_value=ValidatedExtensionTokenResponse(
            user_id=USER_ID,
            email="admin@lecoffre.com",
            display_name="Admin User",
            token_id=TOKEN_ID,
        )
    )
    return usecase


def _bearer(value: str = "a-token"):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=value)


def test_should_return_a_session_principal_when_the_cookie_is_valid():
    principal = get_current_principal(
        request=_request(),
        access_token="valid-cookie",
        credentials=None,
        validate_usecase=_session_usecase(["admin"]),
        validate_extension_usecase=_extension_usecase(),
    )

    assert principal.kind is CredentialKind.SESSION
    assert principal.is_read_only is False
    assert principal.user.roles == ["admin"]


def test_should_strip_the_admin_role_when_authenticating_with_a_bearer():
    # The single most important assertion here. ListPasswordsUseCase hands an
    # admin every password on the instance, and echoing the user's own roles
    # would put that list (names, logins, URLs) into a browser profile.
    extension_usecase = _extension_usecase()

    principal = get_current_principal(
        request=_request(),
        access_token=None,
        credentials=_bearer(),
        validate_usecase=_session_usecase(["admin"]),
        validate_extension_usecase=extension_usecase,
    )

    assert principal.kind is CredentialKind.EXTENSION
    assert principal.user.roles == ["user"]
    assert "admin" not in principal.user.roles


def test_should_ignore_the_bearer_when_a_cookie_is_present():
    extension_usecase = _extension_usecase()

    principal = get_current_principal(
        request=_request(),
        access_token="valid-cookie",
        credentials=_bearer(),
        validate_usecase=_session_usecase(["admin"]),
        validate_extension_usecase=extension_usecase,
    )

    assert principal.kind is CredentialKind.SESSION
    extension_usecase.execute.assert_not_called()


def test_should_reject_when_the_cookie_is_invalid_even_if_a_bearer_is_present():
    # Falling through would let an attacker-supplied bearer rescue an expired
    # cookie, and would break the SPA's 401-then-refresh flow.
    failing_session = Mock(spec=ValidateUserTokenUseCase)
    failing_session.execute = Mock(side_effect=Exception("expired"))
    extension_usecase = _extension_usecase()

    with pytest.raises(HTTPException) as error:
        get_current_principal(
            request=_request(),
            access_token="expired-cookie",
            credentials=_bearer(),
            validate_usecase=failing_session,
            validate_extension_usecase=extension_usecase,
        )

    assert error.value.status_code in (401, 500)
    extension_usecase.execute.assert_not_called()


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_should_refuse_when_a_bearer_attempts_a_mutating_request(method: str):
    with pytest.raises(HTTPException) as error:
        get_current_principal(
            request=_request(method),
            access_token=None,
            credentials=_bearer(),
            validate_usecase=_session_usecase(["user"]),
            validate_extension_usecase=_extension_usecase(),
        )

    assert error.value.status_code == 403


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_should_allow_a_session_to_mutate(method: str):
    principal = get_current_principal(
        request=_request(method),
        access_token="valid-cookie",
        credentials=None,
        validate_usecase=_session_usecase(["user"]),
        validate_extension_usecase=_extension_usecase(),
    )

    assert principal.kind is CredentialKind.SESSION


def test_should_reject_when_no_credential_is_present():
    with pytest.raises(HTTPException) as error:
        get_current_principal(
            request=_request(),
            access_token=None,
            credentials=None,
            validate_usecase=_session_usecase(["user"]),
            validate_extension_usecase=_extension_usecase(),
        )

    assert error.value.status_code == 401


def test_should_report_a_generic_message_when_the_extension_token_is_revoked():
    # A token holder must not be able to tell revoked from expired from unknown.
    revoked = Mock(spec=ValidateExtensionTokenUseCase)
    revoked.execute = Mock(side_effect=ExtensionTokenRevokedError())

    with pytest.raises(HTTPException) as error:
        get_current_principal(
            request=_request(),
            access_token=None,
            credentials=_bearer(),
            validate_usecase=_session_usecase(["user"]),
            validate_extension_usecase=revoked,
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid extension token"


def test_should_match_the_rate_limiter_when_listing_the_bearer_reachable_routes():
    """The list of bearer-reachable paths lives in two places. Keep them equal.

    `RateLimitMiddleware` has to know which routes can authenticate a bearer, so
    it does not spend a database lookup deciding the bucket of a request that is
    going to 401 anyway. That knowledge really lives in the route declarations,
    and a copy of it in the middleware is exactly the kind of restatement that
    drifts in silence: adding a fifth bearer route would leave its callers in
    the anonymous bucket with nothing logged.

    Deriving the truth from the application's own dependency graph also pins the
    containment rule itself, which until now rested on a sentence in CLAUDE.md:
    if somebody adds `get_current_principal` to a route, this test says so.
    """
    from fastapi.routing import APIRoute

    from main import app
    from security.rate_limit_middleware import RateLimitMiddleware

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

    def declares_current_principal(dependant) -> bool:
        if dependant.call is get_current_principal:
            return True
        return any(declares_current_principal(child) for child in dependant.dependencies)

    reachable = {route.path for route in api_routes(app.routes) if declares_current_principal(route.dependant)}

    assert reachable == {
        "/extension/session",
        "/extension/groups",
        "/passwords/list",
        "/passwords/{password_id}",
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
