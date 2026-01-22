from typing import List
from shared_kernel.pubsub import DomainEvent
from shared_kernel.pubsub.adapters.in_memory_event_publisher import (
    InMemoryDomainEventPublisher,
)
from audit_logging_context.domain.log import Log


class InMemoryAuditLogger:
    def __init__(self, event_publisher: InMemoryDomainEventPublisher):
        self._logs: List[Log] = []
        event_publisher.subscribe(DomainEvent, self._handle_event)

    def _handle_event(self, event: DomainEvent):
        self._logs.append(Log(event_type=type(event).__name__, event=event))

    def get_logs(self) -> List[Log]:
        return self._logs
