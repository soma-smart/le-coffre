from enum import Enum


class EventPriority(str, Enum):
    """Priority level for domain events, used for audit logging and alerting."""

    HIGH = "HIGH"  # Critical operations: creation, deletion, sharing
    MEDIUM = "MEDIUM"  # Important operations: updates, configuration changes
    LOW = "LOW"  # Read operations: access, viewing
