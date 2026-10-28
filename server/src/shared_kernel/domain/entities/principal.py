from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

# Enforcing field `id`, that requires hashability, to be `UUID` on the whole system.


@dataclass(kw_only=True)
class Principal(ABC):
    """An actor that performs operations on resources.

    Only the identity lives here. How a principal proved who it is belongs to
    `Credential`, and what it may do is still decided per resource.
    """

    id: UUID

    @abstractmethod
    def _get_display_name(self) -> str:
        """Return how this kind of principal is named to humans."""

    @property
    def display_name(self) -> str:
        """How the principal is named to humans: in histories, listings, notifications."""
        return self._get_display_name()
