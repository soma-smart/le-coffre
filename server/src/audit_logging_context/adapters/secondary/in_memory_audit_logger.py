from typing import List
from shared_kernel.pubsub import DomainEvent
from audit_logging_context.domain.log import Log


class InMemoryAuditLogger:
    def __init__(self):
        self._logs: List[Log] = []

    def _handle_event(self, event: DomainEvent):
        self._logs.append(Log(event_type=type(event).__name__, event=event))

    def get_logs(self) -> List[Log]:
        return self._logs
