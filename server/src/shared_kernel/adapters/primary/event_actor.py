from typing import Literal

from pydantic import BaseModel


class EventActorResponse(BaseModel):
    """Who performed an event, as shown to humans. Shared by every history endpoint."""

    kind: Literal["user", "service_account"]
    display_name: str
