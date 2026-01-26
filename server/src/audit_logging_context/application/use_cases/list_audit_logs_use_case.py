from typing import List

from audit_logging_context.application.commands import ListAuditLogsCommand
from audit_logging_context.application.gateways import (
    AuditLoggerGateway,
)
from audit_logging_context.domain.log import Log


class ListAuditLogsUseCase:
    def __init__(self, audit_logger: AuditLoggerGateway):
        self._audit_logger = audit_logger

    def execute(self, _: ListAuditLogsCommand) -> List[Log]:
        return self._audit_logger.get_logs()
