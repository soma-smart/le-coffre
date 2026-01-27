from audit_logging_context.application.gateways.event_repository import EventRepository


class StoreEventUseCase:
    def __init__(self, event_repository: EventRepository):
        self.event_repository = event_repository

    def execute(self, event):
        self.event_repository.append_event(event)
