from typing import Protocol
from uuid import UUID

from shared_kernel.domain.entities import Principal


class PrincipalRepository(Protocol):
    """Lookup of any principal, whatever its kind."""

    def get_by_id(self, principal_id: UUID) -> Principal | None:
        """Return the principal with this id, as its own kind."""
