from abc import ABC, abstractmethod
from uuid import UUID

from shared_kernel.domain.entities import Principal


class PrincipalRepository(ABC):
    """Lookup of any principal, whatever its kind."""

    @abstractmethod
    def get_by_id(self, principal_id: UUID) -> Principal | None:
        """Return the principal with this id, as its own kind."""
