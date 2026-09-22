from dataclasses import dataclass
from uuid import UUID

from ._command import ServiceAccountCommand


@dataclass
class ListServiceAccountsCommand(ServiceAccountCommand):
    group_id: UUID
    """ID of the group to list the service accounts for."""
