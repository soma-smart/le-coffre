from abc import ABC, abstractmethod

from shared_kernel.domain.entities import Principal
from shared_kernel.domain.value_objects import Credential


class Authenticator[C: Credential](ABC):
    """Turns one kind of `Credential` into the `Principal` it proves."""

    @abstractmethod
    def authenticate(self, credential: C) -> Principal:
        """Return the principal behind this proof.

        Raises:
            AuthenticationError: if it proves no principal.
        """
