from shared_kernel.pubsub.domain.domain_event import DomainEvent


class FakeEventRepository:
    def __init__(self):
        self.events: list[DomainEvent] = []

    def append_event(self, event: DomainEvent) -> None:
        self.events.append(event)

    def list_events(self) -> list[DomainEvent]:
        return self.events
