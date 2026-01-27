from datetime import datetime
from uuid import uuid4

from audit_logging_context.application.commands import CreateAuditLogCommand
from audit_logging_context.application.use_cases import CreateAuditLogUseCase
from shared_kernel.pubsub import DomainEvent


class FakeDomainEvent(DomainEvent):
    """Fake event for testing purposes"""

    def __init__(self, data: str):
        super().__init__(event_id=uuid4(), occurred_on=datetime.now())
        self.data = data


def test_creates_log_from_event(audit_logger):
    # Given
    use_case = CreateAuditLogUseCase(audit_logger)
    event = FakeDomainEvent(data="test_event")
    command = CreateAuditLogCommand(event=event)

    # When
    use_case.execute(command)

    # Then
    logs = audit_logger.get_logs()
    assert len(logs) == 1
    assert logs[0].event_type == "FakeDomainEvent"
    assert logs[0].event == event


def test_creates_multiple_logs(audit_logger):
    # Given
    use_case = CreateAuditLogUseCase(audit_logger)
    event1 = FakeDomainEvent(data="event1")
    event2 = FakeDomainEvent(data="event2")
    command1 = CreateAuditLogCommand(event=event1)
    command2 = CreateAuditLogCommand(event=event2)

    # When
    use_case.execute(command1)
    use_case.execute(command2)

    # Then
    logs = audit_logger.get_logs()
    assert len(logs) == 2
    assert logs[0].event == event1
    assert logs[1].event == event2
