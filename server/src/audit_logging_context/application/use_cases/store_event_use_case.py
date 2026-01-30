from audit_logging_context.application.commands import StoreEventCommand
from audit_logging_context.application.responses import StoreEventResponse
from audit_logging_context.application.gateways.event_repository import EventRepository


class StoreEventUseCase:
    def __init__(self, event_repository: EventRepository):
        self.event_repository = event_repository

    def execute(self, command: StoreEventCommand) -> StoreEventResponse:
        self.event_repository.append_event(command.event)
        return StoreEventResponse()
