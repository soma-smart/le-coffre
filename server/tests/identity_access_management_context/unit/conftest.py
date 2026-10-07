from uuid import UUID

import pytest

from identity_access_management_context.application.gateways import SsoUserInfo
from identity_access_management_context.application.services import ServiceAccountPermissionService
from identity_access_management_context.application.services.authentication import (
    PasswordAuthenticator,
    SSOAuthenticator,
)
from identity_access_management_context.domain.entities import SSOCredentialRecord
from tests.fakes import FakeDomainEventPublisher
from tests.shared_kernel.fakes import FakeTimeGateway

from .fakes import (
    FakeAdminEventRepository,
    FakeAuthSessionRepository,
    FakeGroupEventRepository,
    FakeGroupMemberRepository,
    FakeGroupRepository,
    FakeGroupUsageGateway,
    FakeLoginLockoutGateway,
    FakeOneTimeLinkRevocationGateway,
    FakePasswordCredentialRecordRepository,
    FakePasswordHashingGateway,
    FakePrincipalRepository,
    FakeRevokedTokenRepository,
    FakeServiceAccountEventRepository,
    FakeServiceAccountRepository,
    FakeSsoConfigurationRepository,
    FakeSSOCredentialRecordRepository,
    FakeSsoEncryptionGateway,
    FakeSsoEventRepository,
    FakeSsoGateway,
    FakeTokenCredentialRecordRepository,
    FakeTokenGateway,
    FakeUserEventRepository,
    FakeUserRepository,
)


@pytest.fixture
def user_repository():
    return FakeUserRepository()


@pytest.fixture
def password_credential_record_repository():
    return FakePasswordCredentialRecordRepository()


@pytest.fixture
def password_hashing_gateway():
    return FakePasswordHashingGateway()


@pytest.fixture
def login_lockout_gateway():
    return FakeLoginLockoutGateway()


@pytest.fixture
def token_gateway():
    return FakeTokenGateway()


@pytest.fixture
def revoked_token_repository():
    return FakeRevokedTokenRepository()


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
def sso_credential_record_repository():
    return FakeSSOCredentialRecordRepository()


@pytest.fixture
def principal_repository(user_repository, service_account_repository):
    return FakePrincipalRepository(user_repository, service_account_repository)


@pytest.fixture
def password_authenticator(principal_repository, password_credential_record_repository, password_hashing_gateway):
    return PasswordAuthenticator(
        principal_repository=principal_repository,
        password_credential_record_repository=password_credential_record_repository,
        password_hashing_gateway=password_hashing_gateway,
    )


@pytest.fixture
def sso_authenticator(principal_repository, sso_credential_record_repository):
    return SSOAuthenticator(
        principal_repository=principal_repository,
        sso_credential_record_repository=sso_credential_record_repository,
    )


@pytest.fixture
def group_repository():
    return FakeGroupRepository()


@pytest.fixture
def group_member_repository():
    return FakeGroupMemberRepository()


@pytest.fixture
def one_time_link_revocation_gateway():
    return FakeOneTimeLinkRevocationGateway()


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
def auth_session_repository():
    return FakeAuthSessionRepository()


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


def create_sso_credential(user_id: UUID, sso_user_id: str, sso_provider: str, **kwargs) -> SSOCredentialRecord:
    """Helper to link an existing user to an SSO subject"""
    return SSOCredentialRecord(principal_id=user_id, provider=sso_provider, subject=sso_user_id, **kwargs)


@pytest.fixture
def service_account_repository():
    return FakeServiceAccountRepository()


@pytest.fixture
def token_credential_record_repository():
    return FakeTokenCredentialRecordRepository()


@pytest.fixture
def service_account_event_repository():
    return FakeServiceAccountEventRepository()


@pytest.fixture
def service_account_permission_service(group_repository, group_member_repository):
    return ServiceAccountPermissionService(group_repository, group_member_repository)
