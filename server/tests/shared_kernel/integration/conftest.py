import socket
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from shared_kernel.adapters.secondary import InMemoryDomainEventPublisher
from shared_kernel.domain.entities import DomainEvent


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
    return SampleTestEvent(event_id=uuid4(), occurred_on=datetime.now(), data="test data")


@pytest.fixture
def another_test_event():
    return AnotherSampleTestEvent(event_id=uuid4(), occurred_on=datetime.now(), value=42)


@pytest.fixture
def unreachable_smtp_port():
    """A TCP port with nothing listening on it, to simulate an unreachable SMTP server.

    The socket stays bound (but never listens) for the test's lifetime so no other
    process can claim the port between allocation and the connection attempt.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        yield reserved.getsockname()[1]
