"""The opt-in bearer path, and its containment rules.

`get_current_principal` is the only dependency that accepts a browser-extension
bearer token, and only three read routes declare it. These tests pin the rules
that make that safe.
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
