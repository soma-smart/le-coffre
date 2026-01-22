from shared_kernel.pubsub import DomainEvent
from shared_kernel.pubsub.adapters.in_memory_event_publisher import (
    InMemoryDomainEventPublisher,
)
from audit_logging_context.adapters.secondary import (
    InMemoryAuditLogger,
)
from audit_logging_context.application.use_cases import (
    ListAuditLogsUseCase,
)


class UserCreatedEvent(DomainEvent):
    def __init__(self, user_id: str, username: str):
        self.user_id = user_id
        self.username = username


class PasswordCreatedEvent(DomainEvent):
    def __init__(self, password_id: str, owner_id: str):
        self.password_id = password_id
        self.owner_id = owner_id


def test_list_audit_logs_use_case_returns_empty_list_when_no_events():
    # Given
    event_publisher = InMemoryDomainEventPublisher()
    audit_logger = InMemoryAuditLogger(event_publisher)
    use_case = ListAuditLogsUseCase(audit_logger)

    # When
    logs = use_case.execute()

    # Then
    assert logs == []


def test_list_audit_logs_use_case_returns_logged_events():
    # Given
    event_publisher = InMemoryDomainEventPublisher()
    audit_logger = InMemoryAuditLogger(event_publisher)
    # Subscribe to specific event types
    event_publisher.subscribe(UserCreatedEvent, audit_logger._handle_event)
    event_publisher.subscribe(PasswordCreatedEvent, audit_logger._handle_event)
    use_case = ListAuditLogsUseCase(audit_logger)

    # When
    event_publisher.publish(UserCreatedEvent(user_id="123", username="alice"))
    event_publisher.publish(PasswordCreatedEvent(password_id="456", owner_id="123"))
    logs = use_case.execute()

    # Then
    assert len(logs) == 2
    assert logs[0].event_type == "UserCreatedEvent"
    assert isinstance(logs[0].event, UserCreatedEvent)
    assert logs[0].event.user_id == "123"
    assert logs[0].event.username == "alice"
    assert logs[1].event_type == "PasswordCreatedEvent"
    assert isinstance(logs[1].event, PasswordCreatedEvent)
    assert logs[1].event.password_id == "456"
    assert logs[1].event.owner_id == "123"
