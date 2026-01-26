from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateVaultCommand:
    nb_shares: int
    threshold: int
    setup_id: UUID
