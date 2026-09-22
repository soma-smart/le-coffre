from collections.abc import Hashable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ItemResponse[IdT: Hashable]:
    """Response with an identified item."""

    id: IdT


@dataclass(frozen=True)
class ListResponse[ItemT: ItemResponse]:
    """Response with a sequence of identified items."""

    items: tuple[ItemT, ...]


# Service Account


@dataclass(frozen=True, kw_only=True)
class ServiceAccountResponse: ...


@dataclass(frozen=True, kw_only=True)
class ServiceAccountItemResponse(ServiceAccountResponse, ItemResponse[UUID]): ...


## Concrete responses


@dataclass(frozen=True, kw_only=True)
class CreateServiceAccountResponse(ServiceAccountItemResponse):
    """Response on service account creation."""

    group_id: UUID
    """The ID of the group related to the service account."""

    name: str
    """The name given to the service account."""

    token: str = field(repr=False)
    """The token generated for the service account."""


@dataclass(frozen=True, kw_only=True)
class RotateServiceAccountTokenResponse(ServiceAccountItemResponse):
    """Response on service account token rotation."""

    token: str = field(repr=False)
    """The new token generated for the service account."""


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

    created_by_user_id: UUID | None
    """ID of the user who created the service account."""

    created_by_user_name: str | None
    """Name of the user who created the service account."""

    created_at: datetime | None
    """Time of creation of the service account."""

    revoked_at: datetime | None
    """Time of revocation of the service account."""


@dataclass(frozen=True)
class ListServiceAccountsResponse(ServiceAccountResponse, ListResponse[ServiceAccountSummaryResponse]):
    """Response on service accounts retrieval."""


@dataclass(frozen=True, kw_only=True)
class RevokeServiceAccountResponse(ServiceAccountItemResponse):
    """Response on service account revocation."""
