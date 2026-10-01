from uuid import UUID

import pytest

from identity_access_management_context.application.services.authentication import SessionAuthenticator
from identity_access_management_context.application.use_cases import ValidateUserTokenUseCase
from identity_access_management_context.domain.entities import User, UserPassword
from identity_access_management_context.domain.exceptions import SessionAuthenticationError
from identity_access_management_context.domain.value_objects import SessionToken
from shared_kernel.domain.exceptions import AuthenticationError

USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
EMAIL = "admin@lecoffre.com"
JWT = "jwt_token_for_admin"


@pytest.fixture
def authenticator(
    user_password_repository,
    token_gateway,
    sso_user_repository,
    user_repository,
    revoked_token_repository,
    time_provider,
):
    validate = ValidateUserTokenUseCase(
        user_password_repository,
        token_gateway,
        sso_user_repository,
        user_repository,
        revoked_token_repository,
        time_provider,
    )
    return SessionAuthenticator(validate, user_repository)


@pytest.fixture
def signed_in_user(user_repository, user_password_repository, token_gateway) -> User:
    user = User(id=USER_ID, username="admin", email=EMAIL, name="Admin User")
    user_repository.save(user)
    user_password_repository.save(
        UserPassword(id=USER_ID, email=EMAIL, password_hash=b"hashed_password", display_name="Admin User")
    )
    token_gateway.set_valid_token(JWT, USER_ID, EMAIL, [], {})
    return user


def test_given_a_valid_session_when_authenticating_then_its_user_is_returned(authenticator, signed_in_user):
    assert authenticator.authenticate(SessionToken(JWT)) == signed_in_user


def test_given_an_invalid_session_when_authenticating_then_it_is_refused(authenticator):
    with pytest.raises(SessionAuthenticationError):
        authenticator.authenticate(SessionToken("not-a-session"))


def test_given_a_valid_session_whose_user_is_gone_when_authenticating_then_it_is_refused(
    authenticator, signed_in_user, user_repository
):
    user_repository.delete(signed_in_user.id)

    with pytest.raises(SessionAuthenticationError):
        authenticator.authenticate(SessionToken(JWT))


def test_when_a_session_is_refused_then_it_is_an_authentication_error(authenticator):
    with pytest.raises(AuthenticationError):
        authenticator.authenticate(SessionToken("not-a-session"))
