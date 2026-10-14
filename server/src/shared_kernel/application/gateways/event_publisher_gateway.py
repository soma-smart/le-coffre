from typing import Callable, Protocol, TypeVar

from shared_kernel.domain.entities import DomainEvent

T = TypeVar("T", bound=DomainEvent)


class DomainEventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None:
        """Runs every subscriber of the event. Never raises because of a subscriber:
        a failing one is logged and the others still run."""
        ...

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None: ...
