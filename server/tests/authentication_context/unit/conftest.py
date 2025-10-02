import pytest
from uuid import UUID
from datetime import datetime
from tests.authentication_context.unit.mocks import (
    FakeTokenGateway,
    FakeStateGenerationGateway,
    FakePasswordHashingGateway,
    FakeSessionRepository,
    FakeUserPasswordRepository,
    FakeUserManagementGateway,
    FakeSsoGateway,
    FakeSsoUserRepository,
)
from authentication_context.domain.entities.sso_user import SsoUser


@pytest.fixture
def token_gateway():
    return FakeTokenGateway()


@pytest.fixture
def state_generation_gateway():
    return FakeStateGenerationGateway()


@pytest.fixture
def password_hashing_gateway():
    return FakePasswordHashingGateway()


@pytest.fixture
def session_repository():
    return FakeSessionRepository()


@pytest.fixture
def user_password_repository():
    return FakeUserPasswordRepository()


@pytest.fixture
def user_management_gateway():
    return FakeUserManagementGateway()


@pytest.fixture
def sso_gateway():
    return FakeSsoGateway()


@pytest.fixture
def sso_user_repository():
    return FakeSsoUserRepository()


def create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider):
    """Helper pour créer un SsoUser retourné par le provider (avec UUID temporaire)"""
    return SsoUser(
        internal_user_id=UUID("00000000-0000-0000-0000-000000000000"),
        email=email,
        display_name=display_name,
        sso_user_id=sso_user_id,
        sso_provider=sso_provider,
    )


def create_existing_sso_user(
    user_id, email, display_name, sso_user_id, sso_provider, last_login=None
):
    """Helper pour créer un SsoUser existant en base"""
    return SsoUser(
        internal_user_id=user_id,
        email=email,
        display_name=display_name,
        sso_user_id=sso_user_id,
        sso_provider=sso_provider,
        created_at=datetime.now(),
        last_login=last_login,
    )
