from dataclasses import dataclass

from ._event import ServiceAccountItemEvent


@dataclass(init=False)
class ServiceAccountCreatedEvent(ServiceAccountItemEvent):
    """A service account was created."""
