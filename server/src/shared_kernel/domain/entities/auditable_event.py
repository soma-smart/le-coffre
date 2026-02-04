from typing import Protocol
from uuid import UUID


class AuditableEvent(Protocol):
    """
    Protocol for domain events that can be audited.
    Events implementing this protocol provide metadata for efficient filtering.
    """

    @property
    def bounded_context(self) -> str:
        """The bounded context that produced this event"""
        ...

    @property
    def actor_user_id(self) -> UUID | None:
        """The user who performed the action (who)"""
        ...

    @property
    def target_entity_id(self) -> UUID | None:
        """The entity that was affected by the action (what)"""
        ...

    @property
    def target_entity_type(self) -> str | None:
        """Type of the target entity (password, group, user, vault, etc.)"""
        ...
