import pytest

from rights_access_context.adapters.primary import (
    AccessCheckerAdapter,
)
from .mocks import FakeRightsRepository


@pytest.fixture()
def rights_repository():
    return FakeRightsRepository()


@pytest.fixture()
def access_checker(rights_repository: FakeRightsRepository):
    return AccessCheckerAdapter(rights_repository)
