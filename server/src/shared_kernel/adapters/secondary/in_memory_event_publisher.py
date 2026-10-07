import logging
from typing import Callable

from shared_kernel.domain.entities import DomainEvent

logger = logging.getLogger(__name__)


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
        for handler in [*self._subscribers.get(type(event), []), *self._subscribers.get(DomainEvent, [])]:
            self._notify(handler, event)

    @staticmethod
    def _notify(handler: Callable[[DomainEvent], None], event: DomainEvent) -> None:
        # Subscribers run inside the publisher's use case: one failing must neither
        # fail that use case (a lock must not fail because an email could not be
        # queued) nor keep the other subscribers from running.
        try:
            handler(event)
        except Exception:  # noqa: BLE001 - logged here, never raised into the publisher
            logger.exception(
                "Subscriber %s failed on %s",
                getattr(handler, "__qualname__", repr(handler)),
                type(event).__name__,
            )
