from dataclasses import dataclass

from .get_principal_response import GetPrincipalResponse


@dataclass(frozen=True)
class GroupEventItem:
    """Single group membership event item for response"""

    event_id: str
    event_type: str
    occurred_on: str
    actor_principal_id: str
    actor: GetPrincipalResponse | None
    """None when the actor no longer exists."""
    event_data: dict


@dataclass(frozen=True)
class ListGroupEventsResponse:
    """Response containing list of group membership events"""

    events: list[GroupEventItem]
