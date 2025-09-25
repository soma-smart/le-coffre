from typing import Callable, Dict, List, Type, TypeVar

from shared_kernel.pubsub import DomainEvent

T = TypeVar("T", bound=DomainEvent)


class InMemoryDomainEventPublisher:
    def __init__(self):
        self._subscribers: Dict[
            Type[DomainEvent], List[Callable[[DomainEvent], None]]
        ] = {}

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        # Type: ignore needed because we know at runtime the handler matches the event_type
        self._subscribers[event_type].append(handler)  # type: ignore

    def publish(self, event: DomainEvent) -> None:
        for handler in self._subscribers.get(type(event), []):
            handler(event)
