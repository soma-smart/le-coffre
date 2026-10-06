from dataclasses import dataclass, field
from uuid import UUID

from ._response import ServiceAccountItemResponse


@dataclass(frozen=True, kw_only=True)
class CreateServiceAccountResponse(ServiceAccountItemResponse):
    """Response on service account creation."""

    group_id: UUID
    """The ID of the group related to the service account."""

    name: str
    """The name given to the service account."""

    token: str = field(repr=False)
    """The token generated for the service account."""
