from audit_logging_context.application.gateways.event_repository import EventRepository
from shared_kernel.pubsub.domain.domain_event import DomainEvent


class StoreEventUseCase:
    def __init__(self, event_repository: EventRepository):
        self.event_repository = event_repository

    def execute(self, event: DomainEvent) -> None:
        self.event_repository.append_event(event)
