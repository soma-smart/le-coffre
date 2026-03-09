from typing import Callable

from shared_kernel.domain.entities import DomainEvent


class InMemoryDomainEventPublisher:
    def __init__(self):
        self._subscribers: dict[type[DomainEvent], list[Callable[[DomainEvent], None]]] = {}

    def subscribe_all(self, handler: Callable[[DomainEvent], None]) -> None:
        self._subscribers.setdefault(DomainEvent, []).append(handler)

    def subscribe(self, event_type: type[DomainEvent], handler: Callable[[DomainEvent], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._subscribers.get(type(event), []):
            handler(event)
        for handler in self._subscribers.get(DomainEvent, []):
            handler(event)
