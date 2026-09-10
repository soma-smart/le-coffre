from dataclasses import dataclass


@dataclass(frozen=True)
class GroupEventItem:
    """Single group membership event item for response"""

    event_id: str
    event_type: str
    occurred_on: str
    actor_user_id: str
    actor_email: str | None
    event_data: dict


@dataclass(frozen=True)
class ListGroupEventsResponse:
    """Response containing list of group membership events"""

    events: list[GroupEventItem]
