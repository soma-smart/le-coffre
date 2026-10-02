from dataclasses import dataclass, field

from shared_kernel.domain.value_objects.credential import Credential


@dataclass(frozen=True)
class SessionToken(Credential):
    """The access token a login issued, presented back on each request."""

    value: str = field(repr=False)
