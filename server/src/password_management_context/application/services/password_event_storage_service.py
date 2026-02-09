"""Service for storing password audit events"""

from typing import Any, cast

from password_management_context.application.gateways import (
    PasswordEventRepository,
)
from password_management_context.domain.events import BasePasswordEvent


class PasswordEventStorageService:
    """Application service for storing password events"""

    def __init__(self, repository: PasswordEventRepository):
        self.repository = repository

    def store_event(self, event: BasePasswordEvent) -> None:
        """Store a password domain event"""
        self.repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            password_id=event.password_id,
            actor_user_id=event.get_actor_user_id(),
            event_data=cast(dict[str, Any], event.to_event_data()),
        )
