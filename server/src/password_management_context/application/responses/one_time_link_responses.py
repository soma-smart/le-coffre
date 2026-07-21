from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreatedOneTimeLinkResponse:
    """Returned once, at creation: the only time the raw token ever leaves the server."""

    id: UUID
    token: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True)
class ConsumedOneTimeLinkResponse:
    """The payload handed to the anonymous reader."""

    name: str
    password: str = field(repr=False)
    login: str | None
    url: str | None


@dataclass(frozen=True)
class OneTimeLinkSummaryResponse:
    """Owner-facing view of a link. Deliberately carries no token, not even hashed."""

    id: UUID
    password_id: UUID
    created_by_user_id: UUID
    created_at: datetime
    expires_at: datetime
    read_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class ListOneTimeLinksResponse:
    """A bounded page of links plus how many exist in total.

    `total` is what lets the owner see that older links exist beyond the ones
    returned, rather than silently believing the list is complete. `active` and
    `max_active` let the UI show how much of the cap is used without having to
    re-derive it from a truncated list.
    """

    links: list[OneTimeLinkSummaryResponse]
    total: int
    active: int
    max_active: int


@dataclass(frozen=True)
class OneTimeLinkAuditItemResponse:
    """A link seen from a management table rather than from its own password.

    Carries the password name so the row is readable out of context, and the
    issuer's email for the admin view. Still no token, hashed or otherwise.
    """

    id: UUID
    password_id: UUID
    password_name: str | None
    created_by_user_id: UUID
    created_by_email: str | None
    created_at: datetime
    expires_at: datetime
    read_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class ListOneTimeLinkAuditResponse:
    links: list[OneTimeLinkAuditItemResponse]
    total: int
