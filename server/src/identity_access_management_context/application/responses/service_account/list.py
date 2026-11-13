from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ._response import ListResponse, ServiceAccountItemResponse, ServiceAccountResponse


@dataclass(frozen=True)
class ServiceAccountSummaryResponse(ServiceAccountItemResponse):
    """Manager-facing view of an account. Deliberately carries no token, not even hashed.

    ``created_at`` and the creator fields are optional because they come from the
    account's creation event rather than from its row: an account whose event is
    missing still lists, with those fields empty.
    """

    group_id: UUID
    """The ID of the group related to the service account."""

    name: str
    """The name given to the service account."""

    created_by_principal_id: UUID | None
    """ID of the user who created the service account."""

    created_by_user_name: str | None
    """Name of the user who created the service account."""

    created_at: datetime | None
    """Time of creation of the service account."""

    revoked_at: datetime | None
    """Time of revocation of the service account."""


@dataclass(frozen=True)
class ListServiceAccountsResponse(ServiceAccountResponse, ListResponse[ServiceAccountSummaryResponse]):
    """Response on service accounts retrieval, with how much of the cap the listing uses.

    ``active`` only makes sense against ``max_active`` when the listing was scoped
    to a single group: an unscoped listing spans several groups, each with its own
    budget, so the two numbers then describe different things.
    """

    active: int
    """How many of the listed accounts are still usable."""

    max_active: int
    """How many accounts may be active at once in one group."""
