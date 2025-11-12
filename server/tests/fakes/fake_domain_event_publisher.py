from typing import List, Type, Callable, TypeVar
from shared_kernel.domain.entities import DomainEvent

T = TypeVar("T", bound=DomainEvent)


class FakeDomainEventPublisher:
    def __init__(self):
        self.published_events: List[DomainEvent] = []
        self.subscribers = {}

    def publish(self, event: DomainEvent) -> None:
        self.published_events.append(event)

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    def get_published_events_of_type(self, event_type: Type[T]) -> List[T]:
        return [
            event for event in self.published_events if isinstance(event, event_type)
        ]

    def clear_events(self) -> None:
        self.published_events.clear()
