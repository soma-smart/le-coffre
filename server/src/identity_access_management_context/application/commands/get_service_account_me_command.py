from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetServiceAccountMeCommand:
    service_account_id: UUID
    """The service account the request authenticated as."""
