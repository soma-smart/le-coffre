from dataclasses import dataclass
from typing import List
from vault_management_context.domain.entities import Share


@dataclass(frozen=True)
class ShamirResult:
    shares: List[Share]
    master_key: str
