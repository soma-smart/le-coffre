from uuid import uuid4
from datetime import datetime
import pytest

from shared_kernel.pubsub.domain.domain_event import DomainEvent
from audit_logging_context.application.use_cases.store_event_use_case import (
    StoreEventUseCase,
)


@pytest.fixture
def use_case(event_repository):
    return StoreEventUseCase(event_repository)


def test_given_event_when_store_should_succeed(use_case, event_repository):
    event = DomainEvent(uuid4(), datetime.now())

    use_case.execute(event)

    assert event_repository.events == [event]
