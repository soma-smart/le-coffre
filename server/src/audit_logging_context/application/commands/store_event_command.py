from dataclasses import dataclass
from shared_kernel.domain.entities import DomainEvent


@dataclass
class StoreEventCommand:
    event: DomainEvent
