from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import override
from uuid import UUID

from identity_access_management_context.domain.entities import ServiceAccount


class ServiceAccountRepositoryException(Exception): ...


@dataclass(eq=False)
class CannotRevokeServiceAccount(ServiceAccountRepositoryException):
    service_account_id: UUID

    @override
    def __str__(self) -> str:
        return f"Service account with ID {self.service_account_id} was already revoked."


class ServiceAccountRepository(ABC):
    """Storage for group-owned machine identities."""

    @abstractmethod
    def create(self, accounts: Iterable[ServiceAccount]) -> None:
        """Persist new service accounts."""

    @abstractmethod
    def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[ServiceAccount]:
        """Return the accounts matching these ids, skipping any that do not exist."""

    @abstractmethod
    def list_for_group(self, group_id: UUID) -> Iterable[ServiceAccount]:
        """Return a group's accounts, revoked ones included only on request."""

    @abstractmethod
    def rotate(self, ids: Iterable[UUID]) -> None:
        """Rotate service accounts."""

    @abstractmethod
    def revoke(self, ids: Iterable[UUID]) -> None:
        """Mark service accounts as revoked."""
