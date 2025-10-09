from dataclasses import dataclass
from typing import Optional


@dataclass
class Vault:
    nb_shares: int
    threshold: int
    encrypted_key: str
    setup_id: Optional[str] = None
    status: str = "PENDING"
