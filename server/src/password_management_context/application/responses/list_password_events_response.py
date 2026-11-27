from dataclasses import dataclass


@dataclass(frozen=True)
class EventActor:
    """Who did it, as shown to humans."""

    kind: str
    """`user` or `service_account`."""
    display_name: str


@dataclass(frozen=True)
class PasswordEventItem:
    """Single password event item for response"""

    event_id: str
    event_type: str
    occurred_on: str
    actor_principal_id: str
    actor: EventActor | None
    """None when the actor no longer exists."""
    event_data: dict


@dataclass(frozen=True)
class ListPasswordEventsResponse:
    """Response containing list of password events"""

    events: list[PasswordEventItem]
