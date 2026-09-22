from dataclasses import dataclass

from ._event import ServiceAccountEvent


@dataclass(init=False)
class ServiceAccountRevokedEvent(ServiceAccountEvent):
    """A service account was revoked."""
