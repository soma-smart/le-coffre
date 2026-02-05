"""Service for storing password audit events"""

from password_management_context.application.gateways import (
    PasswordEventRepository,
)
from password_management_context.application.protocols import (
    StorablePasswordEvent,
)


class PasswordEventStorageService:
    """Application service for storing password events

    This service converts password domain events into the format expected
    by the password_event_repository using the StorablePasswordEvent protocol.
    """

    def __init__(self, repository: PasswordEventRepository):
        self.repository = repository

    def store_event(self, event: StorablePasswordEvent) -> None:
        """Store a password event in the password_event_repository"""
        self.repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            password_id=event.password_id,
            actor_user_id=event.get_actor_user_id(),
            event_data=event.to_event_data(),
        )
