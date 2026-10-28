from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetPrincipalCommand:
    principal_id: UUID
