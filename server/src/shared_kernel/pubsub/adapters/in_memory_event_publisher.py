from typing import Callable, Dict, List, Type

from shared_kernel.pubsub import DomainEvent


class InMemoryDomainEventPublisher:
    def __init__(self):
        self._subscribers: Dict[
            Type[DomainEvent], List[Callable[[DomainEvent], None]]
        ] = {}

    def subscribe(
        self, event_type: Type[DomainEvent], handler: Callable[[DomainEvent], None]
    ) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        # Notify subscribers for the exact event type
        for handler in self._subscribers.get(type(event), []):
            handler(event)

        # Notify subscribers for base types (inheritance support)
        for subscribed_type, handlers in self._subscribers.items():
            if subscribed_type is not type(event) and isinstance(
                event, subscribed_type
            ):
                for handler in handlers:
                    handler(event)
