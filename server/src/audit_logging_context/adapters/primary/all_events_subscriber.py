from audit_logging_context.application.use_cases.store_event_use_case import (
    StoreEventUseCase,
)
from audit_logging_context.application.commands import StoreEventCommand


class AllEventsSubscriber:
    def __init__(self, store_event_usecase: StoreEventUseCase) -> None:
        self.store_event_usecase = store_event_usecase

    def __call__(self, event) -> None:
        command = StoreEventCommand(event=event)
        self.store_event_usecase.execute(command)
