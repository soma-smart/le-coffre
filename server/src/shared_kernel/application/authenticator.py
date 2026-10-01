from abc import ABC, abstractmethod

from shared_kernel.domain.entities import Principal
from shared_kernel.domain.value_objects import Authentication


class Authenticator[A: Authentication](ABC):
    """Turns one kind of `Authentication` into the `Principal` it proves."""

    @abstractmethod
    def authenticate(self, authentication: A) -> Principal:
        """Return the principal behind this proof.

        Raises:
            AuthenticationError: if it proves no principal.
        """
