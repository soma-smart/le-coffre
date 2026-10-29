from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, override
from uuid import UUID

from identity_access_management_context.domain.entities import ServiceAccount


class ServiceAccountRepositoryException(Exception): ...


@dataclass(eq=False)
class CannotRevokeServiceAccount(ServiceAccountRepositoryException):
    service_account_id: UUID

    @override
    def __str__(self) -> str:
        return f"Service account with ID {self.service_account_id} cannot be revoked."


class ServiceAccountRepository(Protocol):
    """Storage for group-owned machine identities."""

    def create(self, items: Iterable[ServiceAccount]) -> None:
        """Create new service accounts."""

    def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[ServiceAccount | None]:
        """Return accounts matching these ids."""

    def list_for_groups(self, group_ids: Sequence[UUID]) -> Iterable[ServiceAccount]:
        """Return every account of these groups, revoked ones included."""

    def revoke(self, ids: Iterable[UUID], now: datetime) -> None:
        """Mark service accounts as revoked.

        Raises:
            CannotRevokeServiceAccount: if any account is already revoked.
        """
