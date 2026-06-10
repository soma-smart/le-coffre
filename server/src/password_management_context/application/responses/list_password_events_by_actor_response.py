from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordEventByActorItem:
    """Single password event performed by an actor (includes target password_id)."""

    event_id: str
    event_type: str
    occurred_on: str
    password_id: str
    actor_user_id: str
    event_data: dict


@dataclass(frozen=True)
class ListPasswordEventsByActorResponse:
    """Response containing all password events performed by an actor."""

    events: list[PasswordEventByActorItem]
