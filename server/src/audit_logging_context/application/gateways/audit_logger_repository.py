from typing import List, Protocol
from audit_logging_context.domain.log import Log
from shared_kernel.pubsub import DomainEvent


class AuditLogRepository(Protocol):
    def save_log(self, event: DomainEvent) -> None: ...
    def get_logs(self) -> List[Log]: ...
