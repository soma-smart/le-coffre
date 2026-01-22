import pytest
from uuid import UUID

from identity_access_management_context.adapters.secondary import (
    InMemoryUserRepository,
    InMemorySsoUserRepository,
)
from identity_access_management_context.domain.entities import SsoUser
from identity_access_management_context.application.gateways import SsoUserInfo
from tests.identity_access_management_context.unit.fakes.fake_user_password_repository import (
    FakeUserPasswordRepository,
)
from tests.identity_access_management_context.unit.fakes.fake_password_hashing_gateway import (
    FakePasswordHashingGateway,
)
from tests.identity_access_management_context.unit.fakes.fake_token_gateway import (
    FakeTokenGateway,
)
from tests.identity_access_management_context.unit.fakes.fake_sso_gateway import (
    FakeSsoGateway,
)
from tests.identity_access_management_context.unit.fakes.fake_sso_configuration_repository import (
    FakeSsoConfigurationRepository,
)
from tests.identity_access_management_context.unit.fakes.fake_time_provider import (
    FakeTimeProvider,
)
from tests.identity_access_management_context.unit.fakes.fake_encryption_service import (
    FakeEncryptionService,
)

from tests.identity_access_management_context.unit.fakes.fake_group_repository import (
    FakeGroupRepository,
)
from tests.identity_access_management_context.unit.fakes.fake_group_member_repository import (
    FakeGroupMemberRepository,
)


@pytest.fixture
def user_repository():
    return InMemoryUserRepository()


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
    return FakeTimeProvider()


@pytest.fixture
def encryption_service():
    return FakeEncryptionService()


@pytest.fixture
def sso_gateway():
    return FakeSsoGateway()


@pytest.fixture
def sso_configuration_repository():
    return FakeSsoConfigurationRepository()


@pytest.fixture
def sso_user_repository():
    return InMemorySsoUserRepository()


@pytest.fixture
def group_repository():
    return FakeGroupRepository()


@pytest.fixture
def group_member_repository():
    return FakeGroupMemberRepository()


def create_sso_user_from_provider(
    email: str, display_name: str, sso_user_id: str, sso_provider: str
) -> SsoUserInfo:
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
