from typing import Protocol

from shared_kernel.pubsub.domain.domain_event import DomainEvent


class EventRepository(Protocol):
    def append_event(self, event: DomainEvent) -> None: ...
