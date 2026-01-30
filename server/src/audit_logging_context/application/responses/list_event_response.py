from dataclasses import dataclass
from shared_kernel.domain.entities import DomainEvent


@dataclass(frozen=True)
class ListEventResponse:
    events: list[DomainEvent]
