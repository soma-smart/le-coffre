from rights_access_context.application.use_cases import SetOwnerAccessUseCase
from shared_kernel.pubsub import DomainEventPublisher
from password_management_context.domain.events import PasswordCreatedEvent


class PasswordCreatedSubscriber:
    def __init__(
        self,
        domain_event_subscriber: DomainEventPublisher,
        use_case: SetOwnerAccessUseCase,
    ):
        self.domain_event_subscriber = domain_event_subscriber
        self.use_case = use_case

    def subscribe(self):
        def callback(event: PasswordCreatedEvent) -> None:
            self.use_case.execute(
                user_id=event.created_by, resource_id=event.password_id
            )

        self.domain_event_subscriber.subscribe(PasswordCreatedEvent, callback)
