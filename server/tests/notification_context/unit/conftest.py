import pytest

from tests.shared_kernel.fakes import FakeEmailGateway

from .fakes import FakeGroupOwnershipGateway, FakeNotificationPreferencesRepository, FakeRecipientGateway


@pytest.fixture
def group_ownership_gateway():
    return FakeGroupOwnershipGateway()


@pytest.fixture
def email_gateway():
    return FakeEmailGateway()


@pytest.fixture
def app_base_url():
    return "https://le-coffre.example.com"


@pytest.fixture
def preferences_repository():
    return FakeNotificationPreferencesRepository()


@pytest.fixture
def recipient_gateway():
    return FakeRecipientGateway()
