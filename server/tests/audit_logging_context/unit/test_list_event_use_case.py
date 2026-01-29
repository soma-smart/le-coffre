import pytest
from uuid import uuid4
from datetime import datetime

from audit_logging_context.application.use_cases.list_event_use_case import (
    ListEventUseCase,
)
from shared_kernel.pubsub.domain.domain_event import DomainEvent


@pytest.fixture
def use_case(event_repository):
    return ListEventUseCase(event_repository)


def test_given_empty_event_list_when_listing_events_then_return_empty_list(use_case):
    event_list = use_case.execute()

    assert event_list == []


def test_given_non_empty_event_list_when_listing_events_then_return_event_list(
    use_case,
    event_repository,
):
    event1 = DomainEvent(uuid4(), datetime.now())
    event_repository.append_event(event1)

    event_logs = use_case.execute()

    assert event_logs == [event1]
