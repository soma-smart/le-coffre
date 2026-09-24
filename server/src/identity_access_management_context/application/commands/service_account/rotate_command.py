from dataclasses import dataclass
from uuid import UUID

from ._command import ServiceAccountCommand


@dataclass
class RotateServiceAccountTokenCommand(ServiceAccountCommand):
    service_account_id: UUID
    """ID of the service account to rotate the token of."""
