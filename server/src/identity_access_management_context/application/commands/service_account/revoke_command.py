from dataclasses import dataclass
from uuid import UUID

from ._command import ServiceAccountCommand


@dataclass
class RevokeServiceAccountCommand(ServiceAccountCommand):
    service_account_id: UUID
    """ID of the service account to revoke."""
