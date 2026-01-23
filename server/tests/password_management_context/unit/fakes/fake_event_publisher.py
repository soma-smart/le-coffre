from shared_kernel.pubsub import DomainEvent


class FakeEventPublisher:
    def __init__(self):
        self.published_events = []

    def publish(self, event: DomainEvent) -> None:
        self.published_events.append(event)

    def clear(self):
        self.published_events = []
