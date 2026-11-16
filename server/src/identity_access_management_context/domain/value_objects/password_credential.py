from dataclasses import dataclass, field

from shared_kernel.domain.value_objects.credential import Credential


@dataclass(frozen=True)
class PasswordCredential(Credential):
    """An email and the password a user typed with it."""

    email: str
    password: str = field(repr=False)
