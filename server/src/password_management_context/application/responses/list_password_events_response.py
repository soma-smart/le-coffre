from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordEventItem:
    """Single password event item for response"""

    event_id: str
    event_type: str
    occurred_on: str
    actor_user_id: str
    event_data: dict


@dataclass(frozen=True)
class ListPasswordEventsResponse:
    """Response containing list of password events"""

    events: list[PasswordEventItem]
