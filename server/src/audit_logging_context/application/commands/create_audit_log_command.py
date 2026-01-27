from dataclasses import dataclass
from shared_kernel.pubsub import DomainEvent


@dataclass(frozen=True)
class CreateAuditLogCommand:
    event: DomainEvent
