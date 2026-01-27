from typing import List, Protocol
from audit_logging_context.domain.log import Log


class AuditLogRepository(Protocol):
    def get_logs(self) -> List[Log]: ...
