from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import override
from uuid import UUID

from identity_access_management_context.domain.entities import ServiceAccount


class ServiceAccountRepositoryException(Exception): ...


@dataclass(eq=False)
class CannotRotateServiceAccount(ServiceAccountRepositoryException):
    service_account_id: UUID

    @override
    def __str__(self) -> str:
        return f"Token of service account with ID {self.service_account_id} cannot be rotated."


@dataclass(eq=False)
class CannotRevokeServiceAccount(ServiceAccountRepositoryException):
    service_account_id: UUID

    @override
    def __str__(self) -> str:
        return f"Service account with ID {self.service_account_id} was already revoked."


class ServiceAccountRepository(ABC):
    """Storage for group-owned machine identities."""

    @abstractmethod
    def create(self, items: Iterable[ServiceAccount]) -> None:
        """Create new service accounts."""

    @abstractmethod
    def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[ServiceAccount | None]:
        """Return accounts matching these ids."""

    @abstractmethod
    def list_for_group(self, group_id: UUID) -> Iterable[ServiceAccount]:
        """Return every account of a group, revoked ones included."""

    @abstractmethod
    def rotate(self, ids: Sequence[UUID], hashes: Sequence[str]) -> None:
        """Replace the stored token hash of each account.

        Raises:
            CannotRotateServiceAccount: if any token cannot be rotated.
        """

    @abstractmethod
    def revoke(self, ids: Iterable[UUID], now: datetime) -> None:
        """Mark service accounts as revoked.

        Raises:
            CannotRevokeServiceAccount: if any account is already revoked.
        """
