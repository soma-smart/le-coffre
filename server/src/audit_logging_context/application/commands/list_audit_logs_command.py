from dataclasses import dataclass


@dataclass(frozen=True)
class ListAuditLogsCommand:
    """Command to list audit logs. Can be extended with filters later."""

    pass
