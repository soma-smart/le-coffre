from typing import TypeVar, Type, Callable
from shared_kernel.pubsub import DomainEvent

T = TypeVar("T", bound=DomainEvent)


class FakeEventPublisher:
    def __init__(self):
        self.published_events = []
        self._subscribers = {}

    def publish(self, event: DomainEvent) -> None:
        self.published_events.append(event)

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        pass

    def clear(self) -> None:
        self.published_events.clear()
