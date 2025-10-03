import pytest
from datetime import datetime
from uuid import uuid4, UUID

from shared_kernel.pubsub import DomainEvent, InMemoryDomainEventPublisher


class SampleTestEvent(DomainEvent):
    def __init__(self, event_id: UUID, occurred_on: datetime, data: str):
        super().__init__(event_id, occurred_on)
        self.data = data


class AnotherSampleTestEvent(DomainEvent):
    def __init__(self, event_id: UUID, occurred_on: datetime, value: int):
        super().__init__(event_id, occurred_on)
        self.value = value


@pytest.fixture
def event_publisher():
    return InMemoryDomainEventPublisher()


@pytest.fixture
def test_event():
    return SampleTestEvent(
        event_id=uuid4(), occurred_on=datetime.now(), data="test data"
    )


@pytest.fixture
def another_test_event():
    return AnotherSampleTestEvent(
        event_id=uuid4(), occurred_on=datetime.now(), value=42
    )
