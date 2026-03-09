from uuid import UUID

import pytest

from identity_access_management_context.application.gateways import SsoUserInfo
from identity_access_management_context.domain.entities import SsoUser
from tests.fakes import FakeDomainEventPublisher

from .fakes import (
    FakeAdminEventRepository,
    FakeGroupEventRepository,
    FakeGroupMemberRepository,
    FakeGroupRepository,
    FakeGroupUsageGateway,
    FakePasswordHashingGateway,
    FakeSsoConfigurationRepository,
    FakeSsoEncryptionGateway,
    FakeSsoEventRepository,
    FakeSsoGateway,
    FakeSsoUserRepository,
    FakeTimeGateway,
    FakeTokenGateway,
    FakeUserEventRepository,
    FakeUserPasswordRepository,
    FakeUserRepository,
)


@pytest.fixture
def user_repository():
    return FakeUserRepository()


@pytest.fixture
def user_password_repository():
    return FakeUserPasswordRepository()


@pytest.fixture
def password_hashing_gateway():
    return FakePasswordHashingGateway()


@pytest.fixture
def token_gateway():
    return FakeTokenGateway()


@pytest.fixture
def time_provider():
    return FakeTimeGateway()


@pytest.fixture
def sso_encryption_gateway():
    return FakeSsoEncryptionGateway()


@pytest.fixture
def sso_gateway():
    return FakeSsoGateway()


@pytest.fixture
def sso_configuration_repository():
    return FakeSsoConfigurationRepository()


@pytest.fixture
def sso_user_repository():
    return FakeSsoUserRepository()


@pytest.fixture
def group_repository():
    return FakeGroupRepository()


@pytest.fixture
def group_member_repository():
    return FakeGroupMemberRepository()


@pytest.fixture
def group_usage_gateway():
    return FakeGroupUsageGateway()


@pytest.fixture
def user_event_repository():
    return FakeUserEventRepository()


@pytest.fixture
def group_event_repository():
    return FakeGroupEventRepository()


@pytest.fixture
def sso_event_repository():
    return FakeSsoEventRepository()


@pytest.fixture
def admin_event_repository():
    return FakeAdminEventRepository()


@pytest.fixture
def domain_event_publisher():
    return FakeDomainEventPublisher()


@pytest.fixture
def event_publisher():
    return FakeDomainEventPublisher()


def create_sso_user_from_provider(email: str, display_name: str, sso_user_id: str, sso_provider: str) -> SsoUserInfo:
    """Helper to create SSO user data as returned from provider"""
    return SsoUserInfo(
        email=email,
        display_name=display_name,
        sso_user_id=sso_user_id,
        sso_provider=sso_provider,
    )


def create_existing_sso_user(
    user_id: UUID,
    email: str,
    display_name: str,
    sso_user_id: str,
    sso_provider: str,
    **kwargs,
) -> SsoUser:
    """Helper to create an existing SSO user entity"""
    return SsoUser(
        internal_user_id=user_id,
        email=email,
        display_name=display_name,
        sso_user_id=sso_user_id,
        sso_provider=sso_provider,
        **kwargs,
    )
