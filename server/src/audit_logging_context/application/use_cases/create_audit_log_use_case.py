from audit_logging_context.application.commands import CreateAuditLogCommand
from audit_logging_context.application.gateways import AuditLogRepository


class CreateAuditLogUseCase:
    def __init__(self, audit_logger: AuditLogRepository):
        self._audit_logger = audit_logger

    def execute(self, command: CreateAuditLogCommand) -> None:
        self._audit_logger.save_log(command.event)
