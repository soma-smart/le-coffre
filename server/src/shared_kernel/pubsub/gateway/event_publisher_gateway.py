from typing import Protocol, Type, Callable, TypeVar

from shared_kernel.pubsub import DomainEvent

T = TypeVar("T", bound=DomainEvent)


class DomainEventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None: ...
