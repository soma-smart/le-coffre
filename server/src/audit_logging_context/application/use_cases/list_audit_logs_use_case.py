from typing import List

from audit_logging_context.application.commands import ListAuditLogsCommand
from audit_logging_context.application.gateways import (
    AuditLogRepository,
)
from audit_logging_context.domain.log import Log


class ListAuditLogsUseCase:
    def __init__(self, audit_logger: AuditLogRepository):
        self._audit_logger = audit_logger

    def execute(self, command: ListAuditLogsCommand) -> List[Log]:
        return self._audit_logger.get_logs()
