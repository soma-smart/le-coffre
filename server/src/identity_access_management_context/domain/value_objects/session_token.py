from dataclasses import dataclass, field

from shared_kernel.domain.value_objects.authentication import Authentication


@dataclass(frozen=True)
class SessionToken(Authentication):
    """The access token a login issued, presented back on each request."""

    value: str = field(repr=False)
