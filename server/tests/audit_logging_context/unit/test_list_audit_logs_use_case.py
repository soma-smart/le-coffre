from datetime import datetime
from uuid import uuid4

import pytest

from audit_logging_context.application.use_cases import ListAuditLogsUseCase
from shared_kernel.pubsub import DomainEvent


class FakeDomainEvent(DomainEvent):
    """Fake event for testing purposes"""

    def __init__(self, data: str):
        super().__init__(event_id=uuid4(), occurred_on=datetime.now())
        self.data = data


@pytest.fixture
def use_case(audit_logger):
    """Create the use case with its dependencies"""
    return ListAuditLogsUseCase(audit_logger)


def test_list_audit_logs_use_case_returns_empty_list_when_no_events(use_case):
    # When
    logs = use_case.execute()

    # Then
    assert logs == []


def test_list_audit_logs_use_case_returns_logged_events(audit_logger, use_case):
    # Given
    event1 = FakeDomainEvent(data="event1")
    event2 = FakeDomainEvent(data="event2")

    audit_logger._handle_event(event1)
    audit_logger._handle_event(event2)

    use_case = ListAuditLogsUseCase(audit_logger)

    # When
    logs = use_case.execute()

    # Then
    assert len(logs) == 2
    assert logs[0].event_type == "FakeDomainEvent"
    assert logs[0].event == event1
    assert logs[1].event_type == "FakeDomainEvent"
    assert logs[1].event == event2
