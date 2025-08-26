import pytest

from .mocks import FakeRightsRepository


@pytest.fixture()
def rights_repository():
    return FakeRightsRepository()
