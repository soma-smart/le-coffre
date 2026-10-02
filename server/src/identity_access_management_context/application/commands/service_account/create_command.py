from dataclasses import dataclass
from uuid import UUID

from ._command import ServiceAccountCommand


@dataclass
class CreateServiceAccountCommand(ServiceAccountCommand):
    group_id: UUID
    """ID of the group to create the service account for."""

    name: str
    """Name to give to the service account."""
