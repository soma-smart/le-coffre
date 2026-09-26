import pytest

from tests.shared_kernel.fakes import FakeEmailGateway

from .fakes import FakeGroupOwnershipGateway


@pytest.fixture
def group_ownership_gateway():
    return FakeGroupOwnershipGateway()


@pytest.fixture
def email_gateway():
    return FakeEmailGateway()


@pytest.fixture
def app_base_url():
    return "https://le-coffre.example.com"
