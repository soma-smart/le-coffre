from dataclasses import dataclass

from ._event import ServiceAccountEvent


@dataclass(init=False)
class ServiceAccountCreatedEvent(ServiceAccountEvent):
    """A service account was created."""
