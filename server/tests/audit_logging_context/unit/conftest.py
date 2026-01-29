import pytest


from .fakes.fake_event_repository import (
    FakeEventRepository,
)


@pytest.fixture
def event_repository():
    return FakeEventRepository()
