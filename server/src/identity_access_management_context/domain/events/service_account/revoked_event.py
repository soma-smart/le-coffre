from dataclasses import dataclass

from ._event import ServiceAccountItemEvent


@dataclass(init=False)
class ServiceAccountRevokedEvent(ServiceAccountItemEvent):
    """A service account was revoked."""
