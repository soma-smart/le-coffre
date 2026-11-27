from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetServiceAccountMeResponse:
    service_account_id: UUID
    name: str
    group_id: UUID
    group_name: str
